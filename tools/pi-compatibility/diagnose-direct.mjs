import { readFileSync, writeFileSync } from 'node:fs';
const prior = JSON.parse(readFileSync(new URL('../../docs/evidence/S09_TOOL_DIAGNOSIS_PI.json', import.meta.url)));
const exact = prior.detail.requests[0].body;
const show = await (await fetch('http://127.0.0.1:11434/api/show', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:exact.model}),signal:AbortSignal.timeout(10000)})).json();
const results = [];
const native = {model:exact.model,messages:exact.messages.map(m=>({...m,content:typeof m.content==='string'?m.content:m.content.map(c=>c.text).join('')})),tools:exact.tools,stream:false,options:{num_predict:256}};
const reminder = structuredClone(exact);
reminder.messages[0].content += '\nFor a function call use the model tool protocol: enclose the JSON object in <tool_call> and </tool_call>. Do not print a bare JSON call or invent a tool result.';
for (const [name, path, body] of [['direct_exact','/v1/chat/completions',exact],['native_api','/api/chat',native],['explicit_protocol','/v1/chat/completions',reminder]]) {
 const r = await fetch('http://127.0.0.1:11434'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(60000)});
 const raw = await r.text();
 results.push({name,path,body,status:r.status,raw});
 console.log(name, r.status, raw);
}
writeFileSync(new URL('../../docs/evidence/S09_TOOL_DIAGNOSIS_DIRECT.json',import.meta.url),JSON.stringify({observed_at:new Date().toISOString(),template:show.template,parameters:show.parameters,capabilities:show.capabilities,results},null,2)+'\n');
