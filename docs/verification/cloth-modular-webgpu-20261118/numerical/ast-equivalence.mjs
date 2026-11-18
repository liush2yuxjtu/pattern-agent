import fs from 'node:fs';
import assert from 'node:assert/strict';
import {parse} from './acorn.mjs';
const read=path=>parse(fs.readFileSync(path,'utf8'),{ecmaVersion:'latest',sourceType:'module'});
const original=read('work/cloth-lab/refactor/app.original.js');
const before=new Map(), after=new Map();
function functions(node,map){
 if(!node||typeof node!=='object')return;
 if(node.type==='FunctionDeclaration')map.set(node.id.name,node);
 for(const value of Object.values(node))if(Array.isArray(value))value.forEach(x=>functions(x,map));else if(value&&typeof value==='object')functions(value,map);
}
functions(original,before);
for(const path of ['simulation','diagnostics','replay','persistence','controls','lifecycle'])functions(read(`web/cloth-lab/src/${path}.js`),after);
function isBoundaryGuard(node){
 const isCall=n=>n?.type==='ExpressionStatement'&&n.expression?.callee?.name==='requireRendererAvailable';
 return isCall(node)||(node?.type==='IfStatement'&&node.test?.name==='value'&&isCall(node.consequent));
}
function normalize(node){
 if(!node||typeof node!=='object')return node;
 if(Array.isArray(node))return node.filter(n=>!isBoundaryGuard(n)).map(normalize);
 if(node.type==='MemberExpression'&&node.object.type==='Identifier'&&node.object.name==='S'&&!node.computed)return {type:'Identifier',name:node.property.name};
 return Object.fromEntries(Object.entries(node).filter(([k])=>!['start','end','raw','shorthand'].includes(k)).map(([k,v])=>[k,normalize(v)]));
}
const exact=['getParameters','material','copyTo','floatView','intView','setRunning','sideLength','patternSVG','takeSteps','advance','topologyAudit','captureFrame','startRecording','stopRecording','applyFrame','seekFrame','playReplay','replayTick','replayInfo','stateChanged','download','project','restore','sceneOBJ'];
for(const name of exact)assert.deepEqual(normalize(after.get(name)),normalize(before.get(name)),name);
const wire=before.get('wireUI');
const onchange=wire.body.body.find(n=>n.type==='ExpressionStatement'&&n.expression.type==='AssignmentExpression'&&n.expression.left.type==='MemberExpression'&&n.expression.left.property.name==='onchange'&&n.expression.left.object.arguments?.[0]?.value==='import-replay').expression.right;
assert.deepEqual(normalize(after.get('importReplay').body),normalize(onchange.body),'importReplay callback body');
const save=wire.body.body.find(n=>n.type==='ExpressionStatement'&&n.expression.type==='AssignmentExpression'&&n.expression.left.object?.name==='button'&&n.expression.left.property.name==='onclick').expression.right;
assert.deepEqual(normalize(after.get('saveHTML').body),normalize(save.body),'saveHTML callback body');
const newAnalyze=normalize(after.get('analyze')).body.body,oldAnalyze=normalize(before.get('analyze')).body.body;
const firstRenderGuard=newAnalyze.findIndex(n=>n.type==='IfStatement'&&n.test?.name==='renderBlocked');
assert.deepEqual(newAnalyze.slice(0,firstRenderGuard),oldAnalyze.slice(0,firstRenderGuard),'all physical diagnostics/verdict equations before graphics status');
const rows=body=>body.findIndex(n=>n.type==='VariableDeclaration'&&n.declarations[0].id.name==='rows');
assert.deepEqual(newAnalyze.slice(rows(newAnalyze)),oldAnalyze.slice(rows(oldAnalyze)),'metrics/history after graphics verdict display');
const moduleSetup=normalize(after.get('setupCloth')), oldSetup=normalize(before.get('setupCloth'));
// Only render-resource construction is delegated; all solver/UI statements stay
// in their original order on either side of the new call.
const first=oldSetup.body.body.findIndex(n=>n.type==='IfStatement'&&n.test.name==='cloth');
const last=oldSetup.body.body.findIndex((n,i)=>i>first&&n.type==='ExpressionStatement'&&n.expression?.left?.object?.arguments?.[0]?.value==='width-value');
assert(first>=0&&last>first);
const replacement={type:'ExpressionStatement',expression:{type:'CallExpression',callee:{type:'Identifier',name:'setupClothSurface'},arguments:[],optional:false}};
oldSetup.body.body.splice(first,last-first,replacement);
assert.deepEqual(moduleSetup,oldSetup,'setupCloth excluding moved render-resource block');
console.log(JSON.stringify({mechanicallyEquivalentFunctions:exact.length,boundaryGuardsOnly:true,physicalDiagnosticsEquations:true,importReplayBody:true,saveHTMLBody:true,setupClothSolverAndOrder:true},null,2));
