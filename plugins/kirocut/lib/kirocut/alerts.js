// Alerts for the window and the review page: a soft chime, and a system notice while the tab is hidden, when a video
// leaves Kiro's work (a draft is ready). Loaded by home.html and review.html. Questions are asked in the Kiro chat
// (kirocut_ask), never on these pages.
(()=>{
// Pure, so tests/test_alerts.mjs runs it in node: a video chimes once when its phase goes from Kiro working to anything
// else. firstTime keeps a short list of ids already announced (localStorage), so a reload or a second tab stays quiet.
const WORK=['notes','stills','rendering','cutting'];
const firstTime=(seen,id)=>seen.includes(id)?null:[id,...seen].slice(0,30);
function finished(prev,now){const done=[],next={};
  for(const [d,ph] of Object.entries(now)){const was=prev[d];next[d]=ph;if(WORK.includes(was)&&!WORK.includes(ph))done.push(d)}
  return {done,next}}
if(typeof document==='undefined'){module.exports={firstTime,finished};return}
// a soft two-note chime made here (no audio file); Settings turns it off (localStorage, this browser only)
function chime(){try{const c=new AudioContext();[[660,0],[880,.14]].forEach(([f,t])=>{const o=c.createOscillator(),g=c.createGain(),at=c.currentTime+t;o.frequency.value=f;g.gain.setValueAtTime(.0001,at);
  g.gain.exponentialRampToValueAtTime(.05,at+.02);g.gain.exponentialRampToValueAtTime(.0001,at+.4);o.connect(g).connect(c.destination);o.start(at);o.stop(at+.45)});setTimeout(()=>c.close(),900)}catch(e){}}
const soundOn=()=>{try{return localStorage.getItem('ave-sound')!=='0'}catch(e){return true}};
// the chime, and a system notice while the tab is hidden (permission is asked only from Settings' Turn on alerts)
function alert1(title,body){if(soundOn())chime();
  if(document.hidden&&window.Notification&&Notification.permission==='granted')try{const n=new Notification(title,{body,tag:title});n.onclick=()=>{focus();n.close()}}catch(e){}}
window.aveAlert={alert:alert1,chime,soundOn,finished,firstTime,setSound(on){try{localStorage.setItem('ave-sound',on?'1':'0')}catch(e){}if(on)chime()}};
})();
