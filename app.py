import streamlit as st
import streamlit.components.v1 as components
import base64
import json
from pathlib import Path

st.set_page_config(page_title="接香菸大作戰", page_icon="🎮", layout="wide")

st.markdown("""
<style>
.stApp {background:linear-gradient(135deg,#10152d,#252044);color:white}
h1 {color:#ffd166;text-align:center}
.subtitle {text-align:center;color:#d8dcef}
[data-testid="stFileUploader"] {background:#202747;padding:10px;border-radius:12px}
</style>
""", unsafe_allow_html=True)

st.markdown("# 🎮 接香菸大作戰")
st.markdown('<p class="subtitle">左右移動主角，接住掉落物，挑戰最高分！</p>',
            unsafe_allow_html=True)

# 主角圖片由使用者自行上傳
player_file = st.file_uploader(
    "上傳主角圖片（建議透明背景 PNG）",
    type=["png", "jpg", "jpeg"]
)

def to_data_uri(data, mime):
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"

player_uri = ""
if player_file:
    player_uri = to_data_uri(player_file.getvalue(), player_file.type)

# 讀取從使用者提供的照片中裁切出來的單支香菸素材
cigarette_path = Path(__file__).parent / "cigarette_sprite.png"
if cigarette_path.exists():
    cigarette_uri = to_data_uri(cigarette_path.read_bytes(), "image/png")
else:
    cigarette_uri = ""

player_js = json.dumps(player_uri)
cigarette_js = json.dumps(cigarette_uri)

html = r"""
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<style>
*{box-sizing:border-box}
body{margin:0;background:#10152d;color:white;font-family:Arial,sans-serif;text-align:center}
.container{max-width:900px;margin:auto;padding:10px}
.stats{display:flex;gap:8px;margin:8px 0 12px}
.stat{flex:1;background:#272e50;padding:10px 4px;border-radius:12px;border:1px solid #515d89;font-size:14px}
.stat strong{display:block;color:#ffd166;font-size:22px;margin-top:4px}
canvas{display:block;width:100%;height:auto;background:#151d3b;border:3px solid #ffd166;border-radius:15px;touch-action:none}
button{background:#ffd166;color:#242039;border:0;border-radius:12px;padding:12px 18px;margin:6px 3px;font-size:15px;font-weight:bold;cursor:pointer;touch-action:none}
button:hover{background:#ffad42}
.status{color:#ffd166;font-size:18px;font-weight:bold;min-height:28px;margin-top:8px}
.tip{color:#c4cce5;font-size:13px;line-height:1.6}
</style>
</head>
<body>
<div class="container">
  <div class="stats">
    <div class="stat">🏆 分數<strong id="score">0</strong></div>
    <div class="stat">❤️ 生命<strong id="lives">3</strong></div>
    <div class="stat">⚡ 等級<strong id="level">1</strong></div>
    <div class="stat">👑 最高分<strong id="best">0</strong></div>
  </div>
  <canvas id="game" width="800" height="520"></canvas>
  <div>
    <button onclick="startGame()">▶ 開始</button>
    <button onclick="pauseGame()">⏸ 暫停 / 繼續</button>
    <button onclick="restartGame()">🔄 重新開始</button>
  </div>
  <div>
    <button id="left">⬅ 左移</button>
    <button id="right">右移 ➡</button>
  </div>
  <p class="tip">電腦：使用 ← → 或 A、D。手機：按住左右按鈕，或在遊戲畫面拖曳人物。</p>
  <div class="status" id="message">按下「開始」開始遊戲！</div>
</div>

<script>
const PLAYER_IMAGE = PLAYER_PLACEHOLDER;
const CIGARETTE_IMAGE = CIGARETTE_PLACEHOLDER;
const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
const playerImg = new Image(), cigaretteImg = new Image();
if (PLAYER_IMAGE) playerImg.src = PLAYER_IMAGE;
if (CIGARETTE_IMAGE) cigaretteImg.src = CIGARETTE_IMAGE;

let player = {x:365,y:410,w:76,h:94};
let items=[], particles=[], keys={};
let score=0,lives=3,level=1,best=Number(localStorage.getItem("catchBest")||0);
let running=false,paused=false,gameOver=false;
let lastSpawn=0,lastTime=0,animTime=0,catchEffect=0,direction=0;

function updateStats(){
  document.getElementById("score").textContent=score;
  document.getElementById("lives").textContent=lives;
  document.getElementById("level").textContent=level;
  document.getElementById("best").textContent=best;
}
function drawBackground(){
  const g=ctx.createLinearGradient(0,0,0,520);
  g.addColorStop(0,"#101832");g.addColorStop(1,"#26385e");
  ctx.fillStyle=g;ctx.fillRect(0,0,800,520);
  for(let i=0;i<90;i++){
    ctx.globalAlpha=.25+(i%5)*.1;ctx.fillStyle="#fff";
    ctx.fillRect((i*137)%800,(i*79)%490,2,2);
  }
  ctx.globalAlpha=1;ctx.fillStyle="#34465b";ctx.fillRect(0,500,800,20);
}
function drawPlayer(){
  animTime+=direction!==0?.18:.035;
  const bob=Math.sin(animTime)*2;
  const tilt=direction*.12;
  const jump=catchEffect>0?-Math.sin(catchEffect*Math.PI/1.5)*12:0;
  ctx.save();
  ctx.translate(player.x+player.w/2,player.y+player.h/2+bob+jump);
  ctx.rotate(tilt);
  if(PLAYER_IMAGE && playerImg.complete && playerImg.naturalWidth>0){
    ctx.drawImage(playerImg,-player.w/2,-player.h/2,player.w,player.h);
  }else{
    ctx.font="65px Arial";ctx.textAlign="center";ctx.fillText("🧍",0,24);
  }
  ctx.restore();
  if(catchEffect>0)catchEffect=Math.max(0,catchEffect-.12);
}
function spawnItem(){
  const w=58,h=82;
  items.push({x:Math.random()*(800-w),y:-h,w,h,speed:2+Math.random()*1.2+level*.35,rot:(Math.random()-.5)*.12});
}
function drawItems(){
  items.forEach(o=>{
    ctx.save();ctx.translate(o.x+o.w/2,o.y+o.h/2);ctx.rotate(o.rot);
    if(CIGARETTE_IMAGE && cigaretteImg.complete && cigaretteImg.naturalWidth>0){
      ctx.drawImage(cigaretteImg,-o.w/2,-o.h/2,o.w,o.h);
    }else{
      ctx.font="32px Arial";ctx.textAlign="center";ctx.fillText("🚬",0,10);
    }
    ctx.restore();
  });
}
function makeParticles(x,y){
  for(let i=0;i<12;i++)particles.push({x,y,vx:(Math.random()-.5)*6,vy:(Math.random()-.5)*6,life:1});
}
function drawParticles(){
  particles.forEach(p=>{
    ctx.globalAlpha=p.life;ctx.fillStyle="#ffd166";
    ctx.beginPath();ctx.arc(p.x,p.y,4,0,Math.PI*2);ctx.fill();
    p.x+=p.vx;p.y+=p.vy;p.life-=.035;
  });
  ctx.globalAlpha=1;particles=particles.filter(p=>p.life>0);
}
function movePlayer(delta){
  direction=0;const speed=6*delta;
  if(keys.ArrowLeft||keys.a||keys.A){player.x-=speed;direction=-1;}
  if(keys.ArrowRight||keys.d||keys.D){player.x+=speed;direction=1;}
  player.x=Math.max(0,Math.min(800-player.w,player.x));
}
function update(time){
  if(!running||paused||gameOver)return;
  const delta=lastTime?Math.min((time-lastTime)/16.67,2):1;
  lastTime=time;movePlayer(delta);
  const interval=Math.max(350,1100-level*75);
  if(time-lastSpawn>interval){spawnItem();lastSpawn=time;}
  items.forEach(o=>{
    o.y+=o.speed*delta;
    const hit=o.x<player.x+player.w-8 && o.x+o.w>player.x+8 &&
      o.y+o.h>player.y+10 && o.y<player.y+player.h;
    if(hit&&!o.caught){
      o.caught=true;score+=10;catchEffect=1.5;makeParticles(o.x+o.w/2,o.y+o.h/2);
    }else if(o.y>520&&!o.caught){o.caught=true;lives--;}
  });
  items=items.filter(o=>!o.caught);
  level=Math.floor(score/50)+1;
  if(score>best){best=score;localStorage.setItem("catchBest",best);}
  updateStats();
  if(lives<=0)endGame();
}
function render(){
  drawBackground();drawItems();drawParticles();drawPlayer();
  if(!running||paused){
    ctx.fillStyle="rgba(0,0,0,.42)";ctx.fillRect(0,0,800,520);
    ctx.fillStyle="#ffd166";ctx.font="bold 38px Arial";ctx.textAlign="center";
    ctx.fillText(gameOver?"GAME OVER":paused?"PAUSED":"READY?",400,250);
  }
}
function startGame(){
  if(gameOver){restartGame();return;}
  running=true;paused=false;lastTime=0;
  document.getElementById("message").textContent="遊戲開始！加油！";
}
function pauseGame(){
  if(!running)return;
  paused=!paused;lastTime=0;
  document.getElementById("message").textContent=paused?"遊戲暫停":"繼續挑戰！";
}
function restartGame(){
  score=0;lives=3;level=1;items=[];particles=[];player.x=365;
  running=true;paused=false;gameOver=false;lastSpawn=0;lastTime=0;catchEffect=0;
  updateStats();document.getElementById("message").textContent="重新開始！";
}
function endGame(){
  running=false;gameOver=true;direction=0;
  document.getElementById("message").textContent="遊戲結束！最終分數："+score+" 分";
}
document.addEventListener("keydown",e=>{
  keys[e.key]=true;
  if(["ArrowLeft","ArrowRight"," "].includes(e.key))e.preventDefault();
  if(e.key===" "&&!e.repeat)pauseGame();
});
document.addEventListener("keyup",e=>keys[e.key]=false);
function bindButton(id,key){
  const b=document.getElementById(id);
  b.addEventListener("pointerdown",e=>{e.preventDefault();keys[key]=true;});
  ["pointerup","pointerleave","pointercancel"].forEach(ev=>b.addEventListener(ev,()=>keys[key]=false));
}
bindButton("left","ArrowLeft");bindButton("right","ArrowRight");
function moveByPointer(e){
  const r=canvas.getBoundingClientRect();
  player.x=(e.clientX-r.left)*(800/r.width)-player.w/2;
  player.x=Math.max(0,Math.min(800-player.w,player.x));
}
canvas.addEventListener("pointerdown",e=>{canvas.setPointerCapture(e.pointerId);moveByPointer(e);});
canvas.addEventListener("pointermove",e=>{if(e.pointerType==="touch"||e.buttons===1)moveByPointer(e);});
function loop(t){update(t);render();requestAnimationFrame(loop);}
updateStats();requestAnimationFrame(loop);
</script>
</body>
</html>
"""

html = html.replace("PLAYER_PLACEHOLDER", player_js)
html = html.replace("CIGARETTE_PLACEHOLDER", cigarette_js)

components.html(html, height=760, scrolling=False)
