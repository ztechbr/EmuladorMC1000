const display = document.querySelector('#display');
const screen = document.querySelector('#screen');
const canvas = document.querySelector('#gfx');
const ctx = canvas.getContext('2d', {alpha: false});
const cpu = document.querySelector('#cpu');
const modeLabel = document.querySelector('#mode');
const tapeLabel = document.querySelector('#tape');
const soundLabel = document.querySelector('#sound');

const keyMap = {Enter:'ENTER', Backspace:'BACKSPACE', ' ':'SPACE', Shift:'SHIFT', Control:'CTRL', ArrowUp:'^'};
const shiftedBase = {'!':'1','"':'2','#':'3','$':'4','%':'5','&':'6',"'":'7','(':'8',')':'9','*':':','+':';','<':',','=':'-','>':'.','?':'/'};
function kname(e) {
  if (keyMap[e.key]) return keyMap[e.key];
  if (shiftedBase[e.key]) return shiftedBase[e.key];
  return e.key.length === 1 ? e.key.toUpperCase() : null;
}
async function sendKey(e, down) {
  const k = kname(e);
  if (!k) return;
  e.preventDefault();
  await fetch('/api/key', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key:k,down})});
}
display.addEventListener('keydown', e => sendKey(e, true));
display.addEventListener('keyup', e => sendKey(e, false));
display.addEventListener('pointerdown', () => display.focus());

function bytesFromHex(hex) {
  const out = new Uint8Array(hex.length >> 1);
  for (let i=0,j=0; i<hex.length; i+=2,j++) out[j] = parseInt(hex.slice(i,i+2),16);
  return out;
}

const chars='@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]↑← !"#$%&\'()*+,-./0123456789:;<=>?';
function renderText(vram, ctrl) {
  const orange=!!(ctrl&0x02);
  screen.style.setProperty('--fg',orange?'#ffb700':'#30d200');
  screen.style.setProperty('--bg',orange?'#6b2700':'#007c00');
  const frag = document.createDocumentFragment();
  for (let y=0; y<16; y++) {
    for (let x=0; x<32; x++) {
      const v=vram[y*32+x];
      const ch=chars[v & 0x3f] || '?';
      if (v & 0x80) {
        const span=document.createElement('span'); span.className='inv'; span.textContent=ch; frag.appendChild(span);
      } else frag.appendChild(document.createTextNode(ch));
    }
    if (y!==15) frag.appendChild(document.createTextNode('\n'));
  }
  screen.replaceChildren(frag);
}

// Digital MC6847 renderer. It maps the eight AG modes from GM2..GM0.
// Browser RGB values are presentation approximations; pixel packing/mode sizes
// follow the hardware mode table.
const palette0=[[22,115,48],[238,221,60],[54,95,220],[210,53,45]];
const palette1=[[235,235,220],[35,210,210],[220,65,205],[235,145,35]];
function putScaledPixel(img, logicalW, logicalH, x, y, rgb, scaleX, scaleY) {
  for(let yy=0; yy<scaleY; yy++) for(let xx=0; xx<scaleX; xx++) {
    const px=x*scaleX+xx, py=y*scaleY+yy;
    const off=(py*256+px)*4;
    img.data[off]=rgb[0]; img.data[off+1]=rgb[1]; img.data[off+2]=rgb[2]; img.data[off+3]=255;
  }
}
function renderGraphics(ctrl, vram) {
  const gm=((ctrl>>4)&1)*4+((ctrl>>3)&1)*2+((ctrl>>2)&1);
  const css=!!(ctrl&0x02);
  const resolution=!!(gm&1);
  const cfg=[
    {w:64,h:64,bpr:16,bpp:2},
    {w:128,h:64,bpr:16,bpp:1},
    {w:128,h:64,bpr:32,bpp:2},
    {w:128,h:96,bpr:16,bpp:1},
    {w:128,h:96,bpr:32,bpp:2},
    {w:128,h:192,bpr:16,bpp:1},
    {w:128,h:192,bpr:32,bpp:2},
    {w:256,h:192,bpr:32,bpp:1},
  ][gm];
  const img=ctx.createImageData(256,192);
  const sx=256/cfg.w, sy=192/cfg.h;
  const pal=css?palette1:palette0;
  for(let y=0;y<cfg.h;y++) {
    const rowBase=y*cfg.bpr;
    if(cfg.bpp===1) {
      for(let bx=0;bx<cfg.bpr;bx++) {
        const b=vram[rowBase+bx]||0;
        for(let bit=0;bit<8;bit++) {
          const on=(b>>(7-bit))&1;
          const rgb=on ? (resolution ? [240,240,235] : pal[1]) : (resolution ? [8,8,8] : pal[0]);
          putScaledPixel(img,cfg.w,cfg.h,bx*8+bit,y,rgb,sx,sy);
        }
      }
    } else {
      for(let bx=0;bx<cfg.bpr;bx++) {
        const b=vram[rowBase+bx]||0;
        for(let q=0;q<4;q++) {
          const color=(b>>(6-q*2))&3;
          putScaledPixel(img,cfg.w,cfg.h,bx*4+q,y,pal[color],sx,sy);
        }
      }
    }
  }
  ctx.putImageData(img,0,0);
}

const mcColors=[[48,210,0],[193,229,0],[76,58,180],[154,50,54],[191,200,173],[65,175,113],[200,78,240],[212,127,0]];
function renderSemigraphics(ctrl,vram,sg6) {
  const img=ctx.createImageData(256,192);
  const css=(ctrl&0x02)?1:0;
  const black=[38,48,22];
  for(let cy=0;cy<16;cy++) for(let cx=0;cx<32;cx++) {
    const b=vram[cy*32+cx]||0;
    if(!sg6) {
      const color=mcColors[(b>>4)&7];
      for(let q=0;q<4;q++) {
        const on=(b>>q)&1;
        const qx=q&1, qy=(q>>1)&1;
        const rgb=on?color:black;
        for(let yy=0;yy<6;yy++) for(let xx=0;xx<4;xx++) {
          const x=cx*8+qx*4+xx, y=cy*12+qy*6+yy, o=(y*256+x)*4;
          img.data[o]=rgb[0];img.data[o+1]=rgb[1];img.data[o+2]=rgb[2];img.data[o+3]=255;
        }
      }
    } else {
      const color=mcColors[(css<<2)|((b>>6)&3)];
      for(let q=0;q<6;q++) {
        const on=(b>>q)&1;
        const qx=q&1, qy=(q>>1)&3;
        const rgb=on?color:black;
        for(let yy=0;yy<4;yy++) for(let xx=0;xx<4;xx++) {
          const x=cx*8+qx*4+xx, y=cy*12+qy*4+yy, o=(y*256+x)*4;
          img.data[o]=rgb[0];img.data[o+1]=rgb[1];img.data[o+2]=rgb[2];img.data[o+3]=255;
        }
      }
    }
  }
  ctx.putImageData(img,0,0);
}

let audioCtx=null, master=null, channels=[];
function ensureAudio() {
  if(audioCtx) { audioCtx.resume(); return; }
  audioCtx=new (window.AudioContext||window.webkitAudioContext)();
  master=audioCtx.createGain(); master.gain.value=0.12; master.connect(audioCtx.destination);
  for(let i=0;i<3;i++) {
    const osc=audioCtx.createOscillator(); osc.type='square';
    const gain=audioCtx.createGain(); gain.gain.value=0;
    osc.connect(gain); gain.connect(master); osc.start(); channels.push({osc,gain});
  }
  soundLabel.textContent='ÁUDIO ON';
}
function updateAY(regs, clock) {
  if(!audioCtx) return;
  const mixer=regs[7]||0;
  for(let ch=0;ch<3;ch++) {
    const period=((regs[ch*2+1]&0x0f)<<8)|(regs[ch*2]||0);
    const freq=period?clock/(16*period):clock/16;
    const toneEnabled=((mixer>>ch)&1)===0;
    const vol=regs[8+ch]&0x0f;
    channels[ch].osc.frequency.setTargetAtTime(Math.min(20000,Math.max(20,freq)),audioCtx.currentTime,0.005);
    channels[ch].gain.gain.setTargetAtTime(toneEnabled?(vol/15)*0.22:0,audioCtx.currentTime,0.005);
  }
}

async function poll() {
  try {
    const s=await (await fetch('/api/state')).json();
    const vram=bytesFromHex(s.vram);
    const isCanvas=s.video_mode.kind!=='text';
    screen.style.display=isCanvas?'none':'block';
    canvas.style.display=isCanvas?'block':'none';
    if(s.video_mode.kind==='graphics') renderGraphics(s.vdg_ctrl,vram);
    else if(s.video_mode.kind==='semigraphics') renderSemigraphics(s.vdg_ctrl,vram,s.video_mode.name==='SG6');
    else renderText(vram,s.vdg_ctrl);
    modeLabel.textContent=`${s.video_mode.name} ${s.video_mode.width}x${s.video_mode.height}`;
    tapeLabel.textContent=s.cassette_recording?'FITA REC':(s.cassette_play?'FITA PLAY':'FITA STOP');
    updateAY(s.ay,s.ay_clock);
    const hx=n=>n.toString(16).toUpperCase().padStart(4,'0');
    cpu.textContent=JSON.stringify({PC:hx(s.pc),SP:hx(s.sp),AF:hx(s.af),BC:hx(s.bc),DE:hx(s.de),HL:hx(s.hl),IX:hx(s.ix),IY:hx(s.iy),I:s.i.toString(16).toUpperCase().padStart(2,'0'),R:s.r.toString(16).toUpperCase().padStart(2,'0'),IM:s.im,IFF1:s.iff1,VDG:s.vdg_ctrl.toString(16).toUpperCase().padStart(2,'0'),T:s.tstates,RAM_KB:s.ram_kb,PRINTER:s.printer_bytes},null,2);
  } catch(err) { /* reconnect on next poll */ }
  setTimeout(poll,60);
}
poll();
display.focus();

document.querySelector('#reset').onclick=async()=>{await fetch('/api/reset',{method:'POST'});display.focus()};
document.querySelector('#audio').onclick=()=>{ensureAudio();display.focus()};
document.querySelector('#send').onclick=async()=>{const el=document.querySelector('#type');await fetch('/api/type',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:el.value+'\r'})});display.focus()};
document.querySelector('#type').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();document.querySelector('#send').click()}});
document.querySelector('#wav').onchange=async e=>{if(!e.target.files[0])return;const fd=new FormData();fd.append('file',e.target.files[0]);const r=await fetch('/api/cassette/load',{method:'POST',body:fd});if(!r.ok)alert((await r.json()).error||'WAV inválido');display.focus()};
document.querySelector('#rec').onclick=async()=>{await fetch('/api/cassette/record/start',{method:'POST'});display.focus()};
document.querySelector('#stoprec').onclick=async()=>{const b=await(await fetch('/api/cassette/record/stop',{method:'POST'})).blob();const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='mc1000-save.wav';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);display.focus()};
document.querySelector('#printer').onclick=()=>{const a=document.createElement('a');a.href='/api/printer';a.download='mc1000-printer.bin';a.click();display.focus()};
