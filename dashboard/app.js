import * as pdfjsLib from "/vendor/pdf.mjs";
pdfjsLib.GlobalWorkerOptions.workerSrc="/vendor/pdf.worker.mjs";
const KEY="credit-report-studio-v1",bureaus=["Experian","TransUnion","Equifax"],blank={profile:{},scores:{},insurance:"",marks:[]};
const reportingAgencies=[
  ["Experian","Experian"],["TransUnion","TransUnion"],["Equifax","Equifax"],["Innovis","Innovis"],
  ["LexisNexis","LexisNexis Risk Solutions"],["ChexSystems","ChexSystems"],["EarlyWarning","Early Warning Services"],
  ["ClarityServices","Experian Clarity Services"],["DataX","DataX"],["CoreLogicTeletrack","Teletrack (now DataX)"],["NCTUE","NCTUE"]
];
const disputeChannels={
  Experian:{name:"Experian",mode:"portal",url:"https://www.experian.com/help/dispute-credit/"},
  TransUnion:{name:"TransUnion",mode:"portal",url:"https://www.transunion.com/credit-disputes/dispute-your-credit"},
  Equifax:{name:"Equifax",mode:"portal",url:"https://my.equifax.com/"},
  Innovis:{name:"Innovis",mode:"portal",url:"https://www.innovis.com/personal/disputeResolution"},
  LexisNexis:{name:"LexisNexis Risk Solutions",mode:"assisted",url:"https://consumer.risk.lexisnexis.com/contact"},
  ChexSystems:{name:"ChexSystems",mode:"portal",url:"https://www.chexsystems.com/dispute"},
  EarlyWarning:{name:"Early Warning Services",mode:"document",url:"https://www.earlywarning.com/dispute-file-disclosure"},
  ClarityServices:{name:"Experian Clarity Services",mode:"assisted",url:"https://consumers.clarityservices.com/"},
  DataX:{name:"DataX",mode:"document",url:"https://consumers.dataxltd.com/"},
  CoreLogicTeletrack:{name:"Teletrack (now handled through DataX)",mode:"document",url:"https://consumers.teletrack.com/"},
  NCTUE:{name:"NCTUE",mode:"assisted",url:"https://www.nctue.com/"}
};
let state=JSON.parse(localStorage.getItem(KEY)||"null")||structuredClone(blank);
const $=id=>document.getElementById(id),save=()=>localStorage.setItem(KEY,JSON.stringify(state)),esc=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
$("markBureau").innerHTML=reportingAgencies.map(([value,label])=>`<option value="${value}">${label}</option>`).join("");
$("uploadBureau").innerHTML=reportingAgencies.map(([value,label])=>`<option value="${value}">${label}</option>`).join("");
let extracted=[];

function candidateTitle(lines,index){
  const nearby=lines.slice(Math.max(0,index-3),index+4);
  const labeled=nearby.find(line=>/^(account name|creditor|company|subscriber|furnisher)\s*:/i.test(line));
  if(labeled)return labeled.replace(/^[^:]+:\s*/,"").slice(0,100);
  return nearby.find(line=>line.length>2&&!/account (number|type|status)|balance|date|responsibility/i.test(line))?.slice(0,100)||"Report item";
}
function extractCandidates(text){
  const lines=text.split(/\n+/).map(line=>line.replace(/\s+/g," ").trim()).filter(Boolean);
  const anchors=[];
  lines.forEach((line,index)=>{if(/account (name|number|status|type)|creditor|furnisher|subscriber name|collection|charge.?off|payment status/i.test(line))anchors.push(index)});
  const results=[];
  for(const index of anchors){
    const start=Math.max(0,index-3),end=Math.min(lines.length,index+10),reported=lines.slice(start,end).join("\n");
    if(reported.length<35)continue;
    const fingerprint=reported.toLowerCase().replace(/\d/g,"#").slice(0,180);
    if(results.some(item=>item.fingerprint===fingerprint))continue;
    results.push({title:candidateTitle(lines,index),reported,fingerprint});
    if(results.length>=80)break;
  }
  return results;
}
function transUnionLines(items){
  const sorted=[...items].filter(item=>item.str?.trim()).sort((a,b)=>Math.abs(b.y-a.y)>2?b.y-a.y:a.x-b.x),lines=[];
  for(const item of sorted){const current=lines.at(-1);if(current&&Math.abs(current.y-item.y)<=2)current.parts.push(item);else lines.push({y:item.y,parts:[item]})}
  return lines.map(line=>line.parts.sort((a,b)=>a.x-b.x).map(item=>item.str.trim()).filter(Boolean).join(" ").replace(/\s+/g," ").trim()).filter(Boolean);
}
function extractTransUnionCandidates(pageItems){
  const labels=["Date Opened","Responsibility","Account Type","Loan Type","Balance","Date Updated","Payment Received","Last Payment Made","Pay Status","Terms","Date Closed","High Balance (Hist.)","Credit Limit (Hist.)","Estimated month and year this item will be removed","Maximum Delinquency","Remarks"];
  const labelPattern=new RegExp(`^(${labels.map(label=>label.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")).join("|")})$`,"i"),results=[];
  for(const page of pageItems){
    const items=page.items,headings=items.filter((item,index)=>item.str.trim()&&item.x>=30&&item.x<=50&&item.height>=13.5&&item.height<=16&&items.slice(index+1,index+8).some(next=>next.y<item.y&&item.y-next.y<120&&/^(Address|Phone|Date Opened)$/i.test(next.str.trim()))).sort((a,b)=>b.y-a.y);
    for(let index=0;index<headings.length;index++){
      const heading=headings[index],lower=headings[index+1]?.y??-Infinity,card=items.filter(item=>item.y<=heading.y+2&&item.y>lower+2),lines=transUnionLines(card),fields=[];
      for(let lineIndex=0;lineIndex<lines.length;lineIndex++){
        const label=lines[lineIndex].match(labelPattern)?.[1];if(!label)continue;
        const value=lines[lineIndex+1]&&!labelPattern.test(lines[lineIndex+1])&&!/^Payment History$/i.test(lines[lineIndex+1])?lines[lineIndex+1]:"Not shown";
        fields.push(`${label}: ${value}`);
      }
      if(fields.some(field=>/^Pay Status:|^Account Type:|^Date Opened:/i.test(field)))results.push({title:heading.str.trim(),reported:fields.join("\n"),fingerprint:`tu-${page.page}-${Math.round(heading.y)}`});
    }
  }
  return results;
}
function renderExtracted(){
  $("extractedAccounts").innerHTML=extracted.length?`<div class="form-card"><h3>One choice per account</h3><p class="subtle">Choose only the statement that is true for that specific account. Your choice immediately prepares the matching letter and instructions.</p>${extracted.map((item,index)=>`<div class="mark-card"><div class="row"><strong>${esc(item.title)}</strong>${item.decision?`<span class="badge ${item.decision==="skip"?"no":"yes"}">${esc(item.decision==="fraud"?"Fraud":item.decision==="unknown"?"Not recognized":"Skipped")}</span>`:""}</div><pre>${esc(item.reported)}</pre><div class="quick-actions"><button data-quick="unknown" data-extracted="${index}" class="primary">I don't recognize this</button><button data-quick="fraud" data-extracted="${index}">This is identity theft / fraud</button><button data-quick="skip" data-extracted="${index}">This is mine — skip</button></div></div>`).join("")}</div>`:"";
  document.querySelectorAll("[data-quick]").forEach(button=>button.onclick=()=>applyQuickDecision(Number(button.dataset.extracted),button.dataset.quick));
}
function applyQuickDecision(index,decision){
  const item=extracted[index],bureau=$("uploadBureau").value;item.decision=decision;
  const existing=state.marks.findIndex(mark=>mark.sourceFingerprint===item.fingerprint&&mark.bureau===bureau);
  if(decision==="skip"){if(existing>=0)state.marks.splice(existing,1);save();renderExtracted();renderAll();return}
  const fraud=decision==="fraud",mark={bureau,creditor:item.title,type:fraud?"Identity theft / fraud":"Account ownership",date:"",reported:item.reported,evidenceFacts:fraud?"I did not open, authorize, use, or benefit from this account.":"I do not recognize this account as mine and cannot match it to any account I opened or authorized.",accuracy:"yes",reason:fraud?"I did not open or authorize this account. It appears to result from identity theft.":"I do not recognize this account and dispute that it belongs to me.",documents:[],projectLow:"",projectHigh:"",projectSource:"",disputeKind:decision,sourceFingerprint:item.fingerprint};
  if(existing>=0)state.marks[existing]=mark;else state.marks.push(mark);save();renderExtracted();renderAll();
}
$("scanReport").onclick=async()=>{
  const file=$("reportFile").files[0];if(!file)return alert("Choose a PDF report first.");
  $("scanStatus").textContent="Reading the PDF on this device…";$("scanReport").disabled=true;extracted=[];renderExtracted();
  try{const data=new Uint8Array(await file.arrayBuffer()),pdf=await pdfjsLib.getDocument({data}).promise;let text="";const pageItems=[];for(let pageNumber=1;pageNumber<=pdf.numPages;pageNumber++){const page=await pdf.getPage(pageNumber),content=await page.getTextContent();text+=content.items.map(item=>`${item.str}${item.hasEOL?"\n":" "}`).join("")+"\n";pageItems.push({page:pageNumber,items:content.items.map(item=>({str:item.str,x:item.transform[4],y:item.transform[5],height:item.height}))})}if(text.replace(/\s/g,"").length<80)throw new Error("This appears to be an image-only scan. Export a text-based report PDF or use OCR first.");extracted=$("uploadBureau").value==="TransUnion"?extractTransUnionCandidates(pageItems):extractCandidates(text);const specialized=$("uploadBureau").value==="TransUnion"?" TransUnion tradeline card(s)":" possible report item(s)";$("scanStatus").textContent=extracted.length?`Found ${extracted.length}${specialized}. Review them below.`:"Text was extracted, but no account-like sections were found. Confirm the selected agency matches the PDF, or add the item manually under Report marks.";renderExtracted()}catch(error){$("scanStatus").textContent=`Could not extract this PDF: ${error.message}`}finally{$("scanReport").disabled=false}
};
document.querySelectorAll("nav button").forEach(button=>button.onclick=()=>{document.querySelectorAll("nav button,.tab").forEach(node=>node.classList.remove("active"));button.classList.add("active");$(button.dataset.tab).classList.add("active")});
function renderScores(){
  $("scoreGrid").innerHTML=bureaus.map(b=>{const s=state.scores[b]||{};return `<div class="score-card"><h3>${b}</h3><input inputmode="numeric" data-score="${b}" value="${esc(s.base)}" placeholder="—" aria-label="${b} score"><input class="model" data-model="${b}" value="${esc(s.model)}" placeholder="Model: FICO 8, VantageScore 3.0…"><label>As of<input type="date" data-date="${b}" value="${esc(s.date)}"></label><label>Known Auto Score<input inputmode="numeric" data-auto="${b}" value="${esc(s.auto)}" placeholder="250–900 if provided"></label></div>`}).join("");
  document.querySelectorAll("[data-score],[data-model],[data-date],[data-auto]").forEach(field=>field.onchange=()=>{const b=field.dataset.score||field.dataset.model||field.dataset.date||field.dataset.auto;state.scores[b]??={};if(field.dataset.score)state.scores[b].base=field.value;if(field.dataset.model)state.scores[b].model=field.value;if(field.dataset.date)state.scores[b].date=field.value;if(field.dataset.auto)state.scores[b].auto=field.value;save();renderOverview()});
}
function renderOverview(){
  $("insuranceScore").value=state.insurance||"";$("autoScores").innerHTML=bureaus.map(b=>`<p><strong>${b}:</strong> ${esc(state.scores[b]?.auto||"Not entered")}</p>`).join("");
  const yes=state.marks.filter(m=>m.accuracy==="yes").length,unsure=state.marks.filter(m=>m.accuracy==="unsure").length,no=state.marks.filter(m=>m.accuracy==="no").length;
  $("markSummary").innerHTML=`<p><span class="badge yes">${yes} factual disputes</span> <span class="badge unsure">${unsure} need evidence</span> <span class="badge no">${no} do not dispute</span></p>`;
}
function renderProfile(){for(const id of ["preferredName","state","city","reviewDate","facts"])$(id).value=state.profile[id]||""}
function renderMarks(){
  $("markList").innerHTML=state.marks.map((m,i)=>{
    const projection=m.projectSource
      ? `<p class="subtle">User-supplied simulator scenario: ${esc(m.projectLow)} to ${esc(m.projectHigh)} points · ${esc(m.projectSource)}. Not a prediction.</p>`
      : '<p class="subtle">No point estimate: models depend on the full file and lender-selected version.</p>';
    return `<div class="mark-card"><div class="row"><div><span class="badge ${m.accuracy}">${esc(m.accuracy)}</span> <strong>${esc(m.creditor)}</strong> · ${esc(m.bureau)}</div><button data-delete="${i}">Remove</button></div><p>${esc(m.type)} — ${esc(m.reported)}</p><p class="subtle"><strong>Evidence:</strong> ${esc(m.evidenceFacts||"None recorded")}</p>${projection}</div>`;
  }).join("")||"<p class='subtle'>No report marks added yet.</p>";
  document.querySelectorAll("[data-delete]").forEach(button=>button.onclick=()=>{state.marks.splice(Number(button.dataset.delete),1);save();renderAll()});
}
function letterText(mark){
  const agency=disputeChannels[mark.bureau]?.name||mark.bureau,documents=(mark.documents||[]).map(path=>path.split(/[\\/]/).pop()).filter(Boolean);
  const fraudText=mark.disputeKind==="fraud"?"\n\nThis account was not opened or authorized by me. [If available: I am enclosing my Identity Theft Report and request the identity-theft block available under federal law.]":"";
  return `[Your full legal name]\n[Your mailing address]\n[City, State ZIP]\n[Date]\n\n${agency}\n[Use the current dispute address shown on your report or the official instructions linked below]\n\nRe: Request to reinvestigate inaccurate or incomplete consumer-report information\nReport/reference number: [Reference number, if available]\n\nTo whom it may concern:\n\nI am writing to dispute information in my consumer report that I believe is inaccurate or incomplete.${fraudText}\n\nItem being disputed: ${mark.creditor}\nWhat the report states:\n${mark.reported||"[Describe exactly what the report states]"}\n\nWhy it is inaccurate or incomplete:\n${mark.reason}\n\nFacts and supporting evidence:\n${mark.evidenceFacts||"[Add the facts your records support before sending]"}\n\nPlease conduct a reasonable reinvestigation and correct the information. If the information cannot be verified as complete and accurate, please delete it from my file. Please send me the written results and an updated copy of my consumer report.\n\nEnclosures (copies, not originals):\n${documents.length?documents.map(name=>`- ${name}`).join("\n"):"- [List supporting records]"}\n- [Copy of identification/address proof only if the agency requires it]\n\nSincerely,\n\n[Signature]\n[Printed legal name]`;
}
function filingSteps(channel,mark){
  if(mark.disputeKind==="fraud")return ["Create an official identity-theft recovery plan at IdentityTheft.gov and save the Identity Theft Report.","Contact the creditor's fraud department so it can close or restrict the fraudulent account.","Open the reporting agency's official channel, choose identity theft/account not mine, and attach the requested Identity Theft Report and identification.","Review and submit it yourself, save the confirmation, and consider freezing your consumer reports."];
  if(channel.mode==="portal")return ["Open the official dispute portal and authenticate directly with the agency.","Select the exact report item; do not dispute other accurate information.","Use the letter facts in the portal fields and upload copies of supporting evidence.","Review every statement, submit it yourself, and save the confirmation and result."];
  if(channel.mode==="document")return ["Open the official instructions and confirm the current secure-upload or mailing destination.","Download the letter, replace every placeholder, then print and sign it if mailing.","Include copies—not originals—of relevant evidence and only the identity documents requested.","Use tracked mail or retain the secure-upload receipt, plus a complete copy of what you sent."];
  return ["Open the official consumer-support page and obtain your current disclosure/report first.","Ask the agency to confirm its current dispute delivery method and address.","Complete the generated letter and attach copies of evidence tied to the exact item.","Keep the delivery confirmation and written investigation result."];
}
function renderLetters(){
  const eligible=state.marks.map((mark,index)=>({mark,index})).filter(({mark})=>mark.accuracy==="yes"&&mark.reason);
  $("letterList").innerHTML=eligible.map(({mark,index})=>{const channel=disputeChannels[mark.bureau]||{name:mark.bureau,mode:"assisted",url:"#"},steps=filingSteps(channel,mark);return `<article class="mark-card"><span class="badge yes">Ready to draft</span><h3>${esc(channel.name)} — ${esc(mark.creditor)}</h3><ol>${steps.map(step=>`<li>${esc(step)}</li>`).join("")}</ol>${mark.disputeKind==="fraud"?'<p><a href="https://www.identitytheft.gov/" target="_blank" rel="noopener noreferrer">Start at IdentityTheft.gov</a></p>':""}<p><a href="${esc(channel.url)}" target="_blank" rel="noopener noreferrer">Open official agency instructions</a></p><label>Editable letter<textarea id="letter-${index}" rows="22">${esc(letterText(mark))}</textarea></label><button data-letter-download="${index}" class="primary">Download letter</button> <button data-letter-copy="${index}">Copy letter</button></article>`}).join("")||"<div class='form-card'><p class='subtle'>No letters are ready. Upload a report and choose “I don't recognize this” or “Identity theft / fraud” for the applicable account.</p></div>";
  document.querySelectorAll("[data-letter-download]").forEach(button=>button.onclick=()=>{const index=button.dataset.letterDownload,mark=state.marks[index],name=`${mark.bureau}-${mark.creditor}`.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");const text=$("letter-"+index).value,blob=new Blob([text],{type:"text/plain;charset=utf-8"}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=`${name||"dispute"}-letter.txt`;a.click();URL.revokeObjectURL(a.href)});
  document.querySelectorAll("[data-letter-copy]").forEach(button=>button.onclick=async()=>{const index=button.dataset.letterCopy;try{await navigator.clipboard.writeText($("letter-"+index).value);button.textContent="Copied"}catch{alert("Copy was blocked. Select the letter text and copy it manually.")}});
}
function renderAll(){renderScores();renderOverview();renderProfile();renderMarks();renderLetters()}
$("insuranceScore").onchange=()=>{state.insurance=$("insuranceScore").value;save()};
$("saveProfile").onclick=()=>{for(const id of ["preferredName","state","city","reviewDate","facts"])state.profile[id]=$(id).value.trim();save();renderAll()};
$("addMark").onclick=()=>{const accuracy=document.querySelector('input[name="accuracy"]:checked')?.value;if(!$("markCreditor").value.trim()||!accuracy)return alert("Enter the report item and answer the accuracy question.");state.marks.push({bureau:$("markBureau").value,creditor:$("markCreditor").value.trim(),type:$("markType").value,date:$("markDate").value,reported:$("reported").value.trim(),evidenceFacts:$("evidenceFacts").value.trim(),accuracy,reason:$("reason").value.trim(),documents:$("documents").value.split("\n").map(v=>v.trim()).filter(Boolean),projectLow:$("projectLow").value,projectHigh:$("projectHigh").value,projectSource:$("projectSource").value.trim()});save();["markCreditor","markDate","reported","evidenceFacts","reason","documents","projectLow","projectHigh","projectSource"].forEach(id=>$(id).value="");document.querySelectorAll('input[name="accuracy"]').forEach(r=>r.checked=false);renderAll()};
function download(name,data){const blob=new Blob([JSON.stringify(data,null,2)],{type:"application/json"}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=name;a.click();URL.revokeObjectURL(a.href)}
$("downloadPlan").onclick=()=>{const disputes=state.marks.filter(m=>m.accuracy==="yes"&&m.reason).map(m=>({bureau:m.bureau.toLowerCase().replace(/[^a-z0-9]/g,""),matchText:m.creditor,reason:m.reason,explanation:`Reported: ${m.reported}\nCorrect facts: ${m.evidenceFacts}`,documents:m.documents}));if(!disputes.length)return alert("No marks qualify. Answer Yes and provide a factual reason first.");download("disputes.json",{disputes})};
$("downloadBackup").onclick=()=>download("credit-report-studio-backup.json",state);
$("eraseData").onclick=()=>{if(confirm("Erase all locally stored profile, score, and mark data?")){localStorage.removeItem(KEY);state=structuredClone(blank);renderAll()}};
renderAll();
