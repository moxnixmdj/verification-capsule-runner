import fs from "node:fs";
import { pipeline } from "@huggingface/transformers";

const MODEL = "Xenova/flan-t5-small";
const REVISION = "311454e83bc784267fd7eef5940ee854144abbec";
const DTYPE = "q8";

const tasks = [
  {
    id:"para_1", kind:"paraphrase",
    source:"Mira paid 18 dollars for the blue notebook on Tuesday because she needed it for class.",
    prompt:"Paraphrase the following sentence without changing its meaning: Mira paid 18 dollars for the blue notebook on Tuesday because she needed it for class.",
    must:["mira","18","tuesday"]
  },
  {
    id:"para_2", kind:"paraphrase",
    source:"Orion Labs postponed the satellite launch from May 4 to May 9 because strong winds made the original date unsafe.",
    prompt:"Rewrite this sentence using different wording while preserving every fact: Orion Labs postponed the satellite launch from May 4 to May 9 because strong winds made the original date unsafe.",
    must:["orion","may 4","may 9"]
  },
  {
    id:"para_3", kind:"paraphrase",
    source:"Nadia sent the report to Karim before lunch so he could review it before the meeting.",
    prompt:"Paraphrase without adding or removing facts: Nadia sent the report to Karim before lunch so he could review it before the meeting.",
    must:["nadia","karim"]
  },
  {
    id:"simple_1", kind:"simplify",
    source:"Although the rainfall continued intermittently throughout the morning, the school administrators determined that the outdoor event could proceed once the weather improved.",
    prompt:"Rewrite in simpler English while preserving the meaning: Although the rainfall continued intermittently throughout the morning, the school administrators determined that the outdoor event could proceed once the weather improved.",
    must:["school","event"]
  },
  {
    id:"simple_2", kind:"simplify",
    source:"The committee elected to defer implementation of the revised policy until the legal department had completed its review.",
    prompt:"Make this sentence easier to understand without changing the facts: The committee elected to defer implementation of the revised policy until the legal department had completed its review.",
    must:["committee","legal"]
  },
  {
    id:"simple_3", kind:"simplify",
    source:"Dr. Salma instructed Omar to consume the medication with food in order to reduce the likelihood of stomach irritation.",
    prompt:"Simplify this sentence but keep all important facts: Dr. Salma instructed Omar to consume the medication with food in order to reduce the likelihood of stomach irritation.",
    must:["salma","omar","food"]
  },
  {
    id:"summary_1", kind:"summarize",
    source:"Aster Bakery opened at 6 a.m. on Friday. By noon it had sold 240 loaves of bread. A power outage then stopped the ovens for two hours. The bakery reopened production at 2 p.m. after an electrician restored power.",
    prompt:"Summarize the following text concisely while preserving the key facts: Aster Bakery opened at 6 a.m. on Friday. By noon it had sold 240 loaves of bread. A power outage then stopped the ovens for two hours. The bakery reopened production at 2 p.m. after an electrician restored power.",
    must:["aster","240","power"]
  },
  {
    id:"summary_2", kind:"summarize",
    source:"The Luma research team tested three water filters. Filter A removed 91 percent of the contaminant, Filter B removed 76 percent, and Filter C removed 88 percent. Because Filter A performed best, the team selected it for the next experiment.",
    prompt:"Write a brief faithful summary: The Luma research team tested three water filters. Filter A removed 91 percent of the contaminant, Filter B removed 76 percent, and Filter C removed 88 percent. Because Filter A performed best, the team selected it for the next experiment.",
    must:["luma","91","filter a"]
  },
  {
    id:"summary_3", kind:"summarize",
    source:"Kareem left Qena at 7:10 in the morning by bus. Heavy traffic delayed the trip by 35 minutes. He reached Luxor at 10:25 and immediately called his sister to tell her he had arrived safely.",
    prompt:"Summarize this passage in one concise sentence while preserving the important information: Kareem left Qena at 7:10 in the morning by bus. Heavy traffic delayed the trip by 35 minutes. He reached Luxor at 10:25 and immediately called his sister to tell her he had arrived safely.",
    must:["kareem","qena","luxor"]
  },
  {
    id:"story_1", kind:"story",
    prompt:"Write a short story of at least 35 words about a robot named Nilo who loses a red key, asks a baker named Sana for help, finds the key under a blue cart, and ends happily.",
    must:["nilo","sana","key","cart"], min_words:35
  },
  {
    id:"story_2", kind:"story",
    prompt:"Write a short story of at least 35 words about Lira, a young astronomer, finding a broken telescope on a hill, repairing it with her friend Basim, and seeing a comet that night. End positively.",
    must:["lira","basim","telescope","comet"], min_words:35
  },
  {
    id:"story_3", kind:"story",
    prompt:"Write a short story of at least 35 words about a dog named Rafi carrying a lost green scarf back to its owner Hana after following footprints through a market. The ending must be happy.",
    must:["rafi","hana","scarf","market"], min_words:35
  },
];

function norm(s){return String(s||"").toLowerCase().replace(/\s+/g," ").trim();}
function words(s){return String(s||"").trim().split(/\s+/).filter(Boolean);}
function avgWordLen(s){
  const ws=words(s).map(x=>x.replace(/[^A-Za-z]/g,"")).filter(Boolean);
  return ws.length?ws.reduce((a,b)=>a+b.length,0)/ws.length:0;
}
function containsAll(text, items){const n=norm(text);return items.every(x=>n.includes(norm(x)));}

function scoreTask(t, output){
  const result={must_preserved:containsAll(output,t.must),nonempty:!!norm(output)};
  const ow=words(output).length;
  if(t.kind==="paraphrase"){
    const sw=words(t.source).length;
    result.changed=norm(output)!==norm(t.source);
    result.length_reasonable=ow>=Math.max(4,Math.floor(sw*0.45)) && ow<=Math.ceil(sw*1.55);
    result.pass=result.nonempty&&result.must_preserved&&result.changed&&result.length_reasonable;
  } else if(t.kind==="simplify"){
    const sw=words(t.source).length;
    result.not_longer=ow<=sw+3;
    result.lexically_not_harder=avgWordLen(output)<=avgWordLen(t.source)+0.35;
    result.pass=result.nonempty&&result.must_preserved&&result.not_longer&&result.lexically_not_harder;
  } else if(t.kind==="summarize"){
    const sw=words(t.source).length;
    result.compressed=ow<=Math.floor(sw*0.78);
    result.pass=result.nonempty&&result.must_preserved&&result.compressed;
  } else if(t.kind==="story"){
    result.long_enough=ow>=(t.min_words||35);
    result.pass=result.nonempty&&result.must_preserved&&result.long_enough;
  }
  result.output_words=ow;
  return result;
}

console.log(JSON.stringify({event:"MODEL_LOAD_START",model:MODEL,revision:REVISION,dtype:DTYPE}));
const gen = await pipeline("text2text-generation", MODEL, {
  revision: REVISION,
  dtype: DTYPE,
  device: "wasm",
});
console.log(JSON.stringify({event:"MODEL_LOAD_PASS",model:MODEL,revision:REVISION,dtype:DTYPE}));

const rows=[];
for(const task of tasks){
  const out=await gen(task.prompt,{
    max_new_tokens: task.kind==="story"?120:80,
    do_sample:false,
    num_beams:1,
  });
  const text=String(out?.[0]?.generated_text||"").trim();
  const screen=scoreTask(task,text);
  const row={id:task.id,kind:task.kind,output:text,screen};
  rows.push(row);
  console.log("SEMANTIC_SCREEN_CASE="+JSON.stringify(row));
}

const kinds=["paraphrase","simplify","summarize","story"];
const category={};
for(const k of kinds){
  const xs=rows.filter(x=>x.kind===k);
  category[k]={passed:xs.filter(x=>x.screen.pass).length,total:xs.length};
}
const useful_screen=Object.values(category).every(x=>x.passed>=2);
const receipt={
  schema:"PROJECT_BRAIN_FLAN_T5_SMALL_Q8_SEMANTIC_SEED_SCREEN_V1",
  status:"PUBLIC_NONTERMINAL_SCREEN_COMPLETE",
  model:MODEL,
  revision:REVISION,
  dtype:DTYPE,
  task_count:rows.length,
  category,
  passes_minimum_screen:useful_screen,
  rows,
  hard_nonclaims:[
    "SCREENING_ONLY__NOT_A_LIVEBENCH_SCORE",
    "NO_OPUS55_NONINFERIORITY_PROOF",
    "NO_TERMINAL_CASE_DATA_USED",
    "PASS_DOES_NOT_PROVE_SEMANTIC_EQUIVALENCE_OR_FACTUALITY",
    "FAIL_DOES_NOT_PROVE_NO_USEFUL_CAPABILITY_EXISTS"
  ]
};
fs.writeFileSync("flan_t5_small_semantic_screen_receipt.json",JSON.stringify(receipt,null,2)+"\n");
console.log("SEMANTIC_SCREEN_RESULT="+JSON.stringify({...receipt,rows:undefined}));
await gen.dispose();
