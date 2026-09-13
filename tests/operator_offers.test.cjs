const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../Back/static/index.html'), 'utf8');
const code = html.slice(html.indexOf('    function operatorOffers('), html.indexOf('    function reactionButtons('));
const store = new Map(), rendered = [], boxes = [];
const context = vm.createContext({
  currentChatId: 7, userUuid:'u', Date, WebSocket:{OPEN:1},
  localStorage:{getItem:key=>store.get(key)},
  safeParseLS:(key,fallback)=>store.has(key)?JSON.parse(store.get(key)):fallback,
  setLSObj:(key,value)=>store.set(key,JSON.stringify(value)),
  isSameChat:(a,b)=>String(a)===String(b), getStreamBubble:()=>null,
  appendRenderedMessage:opts=>rendered.push(opts),
  document:{querySelectorAll:selector=>selector.includes('.operator-offer')?boxes:[]},
  socket:{readyState:1,send:raw=>sent.push(JSON.parse(raw))}
});
const sent=[];
vm.runInContext(code,context);
function offer(id,chat=7,requestedAt) {
  return {data:{chat_id:chat,all_text:'Нужен оператор?'}, meta:{is_user_need_support:true,message_id:id,user_query:'Ошибка подписи',offer_requested_at:requestedAt}};
}
function box() {return {removed:false,remove(){this.removed=true;},querySelector:()=>({textContent:''})};}
context.handleOperatorOffer(offer(11),'7');
assert.equal(rendered.length,1);
assert.equal(rendered[0].id,11);
context.handleOperatorOffer(offer(11),'7');
assert.equal(rendered.length,1);
const no=box();context.answerOperatorOffer(11,false,no);
assert(no.removed);assert.equal(sent.length,0);
context.handleOperatorOffer(offer(12),'7');
const yes=box();context.answerOperatorOffer(12,true,yes);context.answerOperatorOffer(12,true,yes);
assert.equal(sent.length,1);
assert.equal(sent[0].event,'SUPPORT_REQUEST');
assert.equal(sent[0].data.chat_id,7);
assert.equal(sent[0].data.text,'Ошибка подписи');
assert(yes.removed);
context.handleOperatorOffer(offer(13),'7');
context.handleOperatorOffer(offer(14,8),'8');
context.dismissOperatorOffers(7);
assert.equal(context.operatorOffers()['13'].status,'declined');
assert.equal(context.operatorOffers()['14'].status,'pending');
context.currentChatId=8;
context.syncOperatorOffersWithHistory('8',[{id:14,user_role:'bot'},{id:15,user_role:'user'}]);
assert.equal(context.operatorOffers()['14'].status,'declined');
store.set('alpha_last_user_send_u_7','2026-09-13T00:01:00Z');
context.handleOperatorOffer(offer(16,7,'2026-09-13T00:00:00Z'),'7');
assert.equal(context.operatorOffers()['16'].status,'declined');
context.handleOperatorOffer(offer(17,8),'8');
context.socket.readyState=0;
const offline=box();context.answerOperatorOffer(17,true,offline);
assert(!offline.removed);assert.equal(context.operatorOffers()['17'].status,'pending');
// The flag is handled before the ordinary per-chat END_GENERATION duplicate guard.
const end=html.slice(html.indexOf('    function handleEndGeneration('),html.indexOf('    function handleServerError('));
const endContext=vm.createContext({normalizeChatId:String,currentChatId:7,
  endReceivedForChat:{'7':true},handleOperatorOffer:()=>{endContext.received=true;}});
vm.runInContext(end,endContext);
endContext.handleEndGeneration(offer(18));assert(endContext.received);
console.log('PASS: offer after completed generation, exact message/chat, duplicate delivery, yes/no, next-message dismissal, late offer, reload sync, offline retry');
