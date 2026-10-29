#!/usr/bin/env python3
"""Local-only HTTP + four-device BLE service for the LYKON Research Console."""
import asyncio, csv, glob, json, mimetypes, os, re, select, struct, sys, termios, threading, time
from collections import deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from bleak import BleakClient, BleakScanner

ROOT=Path(__file__).resolve().parent; PROJECT=ROOT.parent
LOCAL_CAPTURE=PROJECT/"tmp"/"wear_test_01.csv"
SYNTHETIC_CAPTURE=PROJECT/"examples"/"synthetic_session"/"imu_sample.csv"
UUID="5d7a0002-6f7e-4d8b-9a66-7c2e8b7f1000"; AUDIO_UUID="5d7a0004-6f7e-4d8b-9a66-7c2e8b7f1000"
PACKET=struct.Struct("<IIhhhhhh");AUDIO_PACKET=struct.Struct("<IIHH")
PRIVATE_REGISTRY=PROJECT/"configs"/"device_registry.local.json"
def load_registry():
 default={"imu_devices":[{"name":f"LYKON-{i:03d}","sensor":f"IMU{i:03d}","usb_serial":"LOCAL_ONLY"} for i in range(1,5)],"uwb_tag":{"logical_id":"UWB-TAG-001","usb_serial":"LOCAL_ONLY"}}
 if PRIVATE_REGISTRY.is_file():
  with PRIVATE_REGISTRY.open(encoding="utf-8") as f:return json.load(f)
 return default
REGISTRY=load_registry()
TARGETS=[{"name":d["name"],"sensor":d["sensor"],"usbSerial":d.get("usb_serial","LOCAL_ONLY")} for d in REGISTRY["imu_devices"]]
DEVICES=TARGETS
FIELDS="session_id sensor_id seq t_node_us host_received_us synced_timestamp_us ax ay az gx gy gz".split()
AUDIO_FIELDS="session_id sensor_id seq t_node_us host_received_us synced_timestamp_us rms_pcm peak_pcm".split()
UWB_TAG_SERIAL=REGISTRY["uwb_tag"].get("usb_serial","LOCAL_ONLY")
UWB_FIELDS="session_id tag_id host_received_us sequence block anchor_id status distance_cm".split()
UWB_MEASUREMENT=re.compile(r'mac_address=0x(?P<peer>[0-9a-fA-F]+),\s*status="(?P<status>[^"]+)"(?:,\s*distance\[cm\]=(?P<distance>-?\d+))?')
UWB_SEQUENCE=re.compile(r"sequence_number=(?P<sequence>\d+),\s*block_index=(?P<block>\d+)")

class Clock:
 def __init__(self): self.prev=None; self.epoch=0; self.offset=None
 def align(self,raw,host):
  if self.prev is not None and raw<self.prev and self.prev-raw>0x80000000:self.epoch+=1<<32
  self.prev=raw; node=self.epoch+raw
  if self.offset is None:self.offset=host-node
  return node,node+self.offset

class Fleet:
 def __init__(self):
  self.lock=threading.RLock(); self.tasks={}; self.recording=False; self.session=None; self.files={}; self.writers={};self.audioFiles={};self.audioWriters={}
  self.states={d["name"]:{**d,"status":"waiting" if d in TARGETS else "registered","received":0,"missing":0,"lastSeq":None,"lastSeenUs":None,"samples":deque(maxlen=1200),"clock":Clock(),"audioReceived":0,"audioLastSeq":None,"audioLastSeenUs":None,"audioSamples":deque(maxlen=1200),"audioClock":Clock(),"audioAvailable":None,"connections":0,"sequenceResets":0,"error":None} for d in DEVICES}
 def start(self): threading.Thread(target=lambda:asyncio.run(self.run()),daemon=True).start()
 async def run(self):
  while True:
   needed=[d for d in TARGETS if d["name"] not in self.tasks or self.tasks[d["name"]].done()]
   if needed:
    with self.lock:
     for d in needed:self.states[d["name"]]["status"]="scanning"
    try:
     found=await BleakScanner.discover(timeout=3,return_adv=True); advertised={}
     for device,adv in found.values():
      name=adv.local_name or device.name
      if name:advertised[name]=device
     for d in needed:
      if d["name"] in advertised:self.tasks[d["name"]]=asyncio.create_task(self.connect(d,advertised[d["name"]]))
    except Exception as e:
     with self.lock:
      for d in needed:self.states[d["name"]]["error"]=str(e)
   await asyncio.sleep(2)
 async def connect(self,item,device):
  name=item["name"]
  with self.lock:
   state=self.states[name]
   state.update(status="connecting",error=None,lastSeq=None,clock=Clock(),audioLastSeq=None,audioClock=Clock(),audioAvailable=None)
  try:
   async with BleakClient(device) as client:
    with self.lock:
     self.states[name]["status"]="connected"
     self.states[name]["connections"]+=1
    await client.start_notify(UUID,lambda _,data:self.packet(name,data))
    try:
     await client.start_notify(AUDIO_UUID,lambda _,data:self.audio_packet(name,data))
     with self.lock:self.states[name]["audioAvailable"]=True
    except Exception as audio_error:
     # Older IMU-only firmware does not expose the optional audio-level
     # characteristic. Keep the primary IMU connection alive in that case.
     with self.lock:
      self.states[name]["audioAvailable"]=False
      self.states[name]["error"]=f"Audio unavailable; IMU remains connected ({audio_error})"
    while client.is_connected:await asyncio.sleep(.5)
  except Exception as e:
   with self.lock:self.states[name]["error"]=str(e)
  finally:
   with self.lock:self.states[name]["status"]="scanning"
 def packet(self,name,data):
  if not data or len(data)%PACKET.size:return
  host=time.time_ns()//1000
  with self.lock:
   s=self.states[name]
   for offset in range(0,len(data),PACKET.size):
    seq,raw,ax,ay,az,gx,gy,gz=PACKET.unpack_from(data,offset)
    if s["lastSeq"] is not None:
     delta=(seq-s["lastSeq"])&0xffffffff
     if 1<delta<0x80000000:s["missing"]+=delta-1
     elif delta>=0x80000000:s["sequenceResets"]+=1
    s["lastSeq"]=seq;s["received"]+=1;node,synced=s["clock"].align(raw,host)
    sample={"seq":seq,"t_node_us":node,"host_us":host,"synced_us":synced,"a":[ax/1000,ay/1000,az/1000],"g":[gx/10,gy/10,gz/10]}
    s["samples"].append(sample);s["lastSeenUs"]=host
    if self.recording and name in self.writers:self.writers[name].writerow(dict(session_id=self.session,sensor_id=s["sensor"],seq=seq,t_node_us=node,host_received_us=host,synced_timestamp_us=synced,ax=sample["a"][0],ay=sample["a"][1],az=sample["a"][2],gx=sample["g"][0],gy=sample["g"][1],gz=sample["g"][2]))
 def audio_packet(self,name,data):
  if not data or len(data)!=AUDIO_PACKET.size:return
  host=time.time_ns()//1000;seq,raw,rms,peak=AUDIO_PACKET.unpack(data)
  with self.lock:
   s=self.states[name];node,synced=s["audioClock"].align(raw,host);s["audioLastSeq"]=seq;s["audioReceived"]+=1;s["audioLastSeenUs"]=host
   sample={"seq":seq,"t_node_us":node,"host_us":host,"synced_us":synced,"rms":rms,"peak":peak};s["audioSamples"].append(sample)
   if self.recording and name in self.audioWriters:self.audioWriters[name].writerow(dict(session_id=self.session,sensor_id=s["sensor"],seq=seq,t_node_us=node,host_received_us=host,synced_timestamp_us=synced,rms_pcm=rms,peak_pcm=peak))
 def record(self,requested=None):
  with self.lock:
   if self.recording:return self.session
   safe=re.sub(r"[^A-Za-z0-9_-]","_",requested or "")[:64];self.session=safe or datetime.now().strftime("LIVE_%Y%m%d_%H%M%S")
   folder=PROJECT/"data"/"local_capture"/self.session;folder.mkdir(parents=True,exist_ok=True)
   for d in TARGETS:
    f=(folder/f"{d['sensor']}.csv").open("w",newline="",encoding="utf-8");w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();self.files[d["name"]]=f;self.writers[d["name"]]=w
    af=(folder/f"AUDIO_{d['sensor']}.csv").open("w",newline="",encoding="utf-8");aw=csv.DictWriter(af,fieldnames=AUDIO_FIELDS);aw.writeheader();self.audioFiles[d["name"]]=af;self.audioWriters[d["name"]]=aw
   self.recording=True;return self.session
 def stop(self):
  with self.lock:
   self.recording=False
   for f in self.files.values():f.flush();f.close()
   for f in self.audioFiles.values():f.flush();f.close()
   self.files.clear();self.writers.clear();self.audioFiles.clear();self.audioWriters.clear();return self.session
 def snapshot(self):
  with self.lock:
   out=[]
   for d in DEVICES:
    s=self.states[d["name"]];total=s["received"]+s["missing"]
    out.append({k:s[k] for k in ("name","sensor","status","received","missing","lastSeq","lastSeenUs","audioReceived","audioLastSeq","audioLastSeenUs","audioAvailable","connections","sequenceResets","error")}|{"reconnects":max(0,s["connections"]-1),"lossPercent":round(100*s["missing"]/total,3) if total else 0,"samples":list(s["samples"])[-30:],"audioSamples":list(s["audioSamples"])[-30:]})
   return {"devices":out,"recording":self.recording,"sessionId":self.session}

class UwbMonitor:
 def __init__(self):
  self.lock=threading.RLock();self.status="waiting";self.port=None;self.error=None;self.sequence=None;self.block=None;self.received=0;self.lastSeenUs=None
  self.latest={f"0x{i:04x}":{"anchorId":f"UWB-A{i}","address":f"0x{i:04x}","status":"waiting","distanceCm":None,"lastSeenUs":None} for i in range(1,4)}
  self.recording=False;self.session=None;self.file=None;self.writer=None;self.running=True
 def start(self):threading.Thread(target=self.run,daemon=True).start()
 def configure(self,fd):
  attrs=termios.tcgetattr(fd);attrs[0]=0;attrs[1]=0;attrs[2]=termios.CS8|termios.CREAD|termios.CLOCAL;attrs[3]=0;attrs[4]=termios.B115200;attrs[5]=termios.B115200;attrs[6][termios.VMIN]=0;attrs[6][termios.VTIME]=0;termios.tcsetattr(fd,termios.TCSANOW,attrs);termios.tcflush(fd,termios.TCIOFLUSH)
 def find_port(self):
  ports=glob.glob(f"/dev/cu.usbmodem{UWB_TAG_SERIAL}*");return ports[0] if ports else None
 def run(self):
  while self.running:
   port=self.find_port()
   if not port:
    with self.lock:self.status="waiting";self.port=None
    time.sleep(1);continue
   fd=None
   try:
    with self.lock:self.status="connecting";self.port=port;self.error=None
    fd=os.open(port,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK);self.configure(fd);os.write(fd,b"STOP\r\n");time.sleep(.25);termios.tcflush(fd,termios.TCIFLUSH);os.write(fd,b"INITF -MULTI -ADDR=0 -PADDR=[1,2,3]\r\n")
    with self.lock:self.status="connected"
    pending=""
    while self.running and self.find_port()==port:
     ready,_,_=select.select([fd],[],[],.25)
     if not ready:continue
     pending+=os.read(fd,4096).decode("utf-8",errors="replace")
     while "\n" in pending:
      line,pending=pending.split("\n",1);self.line(line)
   except Exception as e:
    with self.lock:self.status="error";self.error=str(e)
    time.sleep(1)
   finally:
    if fd is not None:
     try:os.write(fd,b"STOP\r\n")
     except OSError:pass
     try:os.close(fd)
     except OSError:pass
 def line(self,line):
  seq=UWB_SEQUENCE.search(line)
  if seq:self.sequence=int(seq.group("sequence"));self.block=int(seq.group("block"))
  match=UWB_MEASUREMENT.search(line)
  if not match:return
  now=time.time_ns()//1000;address=f"0x{int(match.group('peer'),16):04x}";distance=match.group("distance")
  with self.lock:
   item=self.latest.setdefault(address,{"anchorId":address,"address":address});item.update(status=match.group("status"),distanceCm=int(distance) if distance is not None else None,lastSeenUs=now);self.received+=1;self.lastSeenUs=now
   if self.recording and self.writer:
    self.writer.writerow(dict(session_id=self.session,tag_id="UWB-TAG-001",host_received_us=now,sequence=self.sequence,block=self.block,anchor_id=item["anchorId"],status=item["status"],distance_cm=item["distanceCm"] if item["distanceCm"] is not None else ""));self.file.flush()
 def record(self,session):
  with self.lock:
   if self.recording:return
   folder=PROJECT/"data"/"local_capture"/session;folder.mkdir(parents=True,exist_ok=True);self.file=(folder/"UWB.csv").open("w",newline="",encoding="utf-8");self.writer=csv.DictWriter(self.file,fieldnames=UWB_FIELDS);self.writer.writeheader();self.recording=True;self.session=session
 def stop_record(self):
  with self.lock:
   self.recording=False
   if self.file:self.file.flush();self.file.close()
   self.file=None;self.writer=None
 def snapshot(self):
  with self.lock:return {"tagId":"UWB-TAG-001","status":self.status,"connected":bool(self.port),"received":self.received,"lastSeenUs":self.lastSeenUs,"error":self.error,"anchors":list(self.latest.values())}

def replay():
 capture=LOCAL_CAPTURE if LOCAL_CAPTURE.is_file() else SYNTHETIC_CAPTURE
 with capture.open(newline="",encoding="utf-8") as f:rows=list(csv.DictReader(f))
 t0=int(rows[0]["t_node_us"]);samples=[];missing=0;prev=None
 for r in rows:
  seq=int(r["seq"]);missing+=((seq-prev-1)&0xffffffff) if prev is not None else 0;prev=seq
  samples.append({"t":round((int(r["t_node_us"])-t0)/1e6,5),"seq":seq,"a":[float(r[k]) for k in ("ax","ay","az")],"g":[float(r[k]) for k in ("gx","gy","gz")]})
 duration=samples[-1]["t"]
 devices=[{"name":d["name"],"sensor":d["sensor"]} for d in DEVICES]
 return {"samples":samples,"devices":devices,"summary":{"sessionId":rows[0]["session_id"],"playerId":rows[0].get("player_id") or rows[0].get("participant_code","P_SYNTH_001"),"sensorId":rows[0]["sensor_id"],"side":rows[0].get("side","right"),"duration":round(duration,2),"sampleRate":round((len(samples)-1)/duration,2),"received":len(samples),"missing":missing,"lossPercent":round(100*missing/(len(samples)+missing),3),"source":str(capture.relative_to(PROJECT))}}

FLEET=Fleet();UWB=UwbMonitor()
def start_capture(requested=None):
 session=FLEET.record(requested);UWB.record(session);return session
def stop_capture():
 session=FLEET.stop();UWB.stop_record();return session
class Handler(BaseHTTPRequestHandler):
 protocol_version="HTTP/1.1"
 def json(self,value,status=200):
  data=json.dumps(value,ensure_ascii=False,separators=(",",":")).encode();self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(data)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(data)
 def do_GET(self):
  path=urlparse(self.path).path
  if path=="/api/bootstrap":self.json(replay());return
  if path=="/api/live/status":self.json(FLEET.snapshot()|{"uwb":UWB.snapshot()});return
  if path=="/api/live/stream":
   self.send_response(200);self.send_header("Content-Type","text/event-stream");self.send_header("Cache-Control","no-cache");self.send_header("Connection","keep-alive");self.end_headers()
   try:
    while True:self.wfile.write(("data:"+json.dumps(FLEET.snapshot()|{"uwb":UWB.snapshot()},ensure_ascii=False,separators=(",",":"))+"\n\n").encode());self.wfile.flush();time.sleep(.15)
   except (BrokenPipeError,ConnectionResetError):pass
   return
  target=(ROOT/(path.lstrip("/") or "index.html")).resolve()
  if (ROOT not in target.parents and target!=ROOT) or not target.is_file():self.send_error(404);return
  body=target.read_bytes();self.send_response(200);self.send_header("Content-Type",mimetypes.guess_type(target.name)[0] or "application/octet-stream");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))) or b"{}")
  if self.path=="/api/live/start":self.json({"ok":True,"sessionId":start_capture(body.get("sessionId"))})
  elif self.path=="/api/live/stop":self.json({"ok":True,"sessionId":stop_capture()})
  else:self.json({"error":"not found"},404)
 def log_message(self,*_):pass
class Server(ThreadingHTTPServer):daemon_threads=True
def main():
 port=int(sys.argv[1]) if len(sys.argv)>1 else 8765;FLEET.start();UWB.start();server=Server(("127.0.0.1",port),Handler)
 print(f"LYKON Research Console: http://127.0.0.1:{port}\nLive BLE targets: LYKON-001 through LYKON-004\nLive UWB tag: {UWB_TAG_SERIAL}\nLocal only. No data is uploaded.",flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:stop_capture();UWB.running=False
if __name__=="__main__":main()
