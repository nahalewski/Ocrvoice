const KEY="credit-report-studio-v1",bureaus=["Experian","TransUnion","Equifax"],blank={profile:{},scores:{},insurance:"",marks:[]};
const reportingAgencies=[
  ["Experian","Experian"],["TransUnion","TransUnion"],["Equifax","Equifax"],["Innovis","Innovis"],
  ["LexisNexis","LexisNexis Risk Solutions"],["ChexSystems","ChexSystems"],["EarlyWarning","Early Warning Services"],
  ["ClarityServices","Experian Clarity Services"],["DataX","DataX"],["CoreLogicTeletrack","Teletrack (now DataX)"],["NCTUE","NCTUE"]
];
let state=JSON.parse(localStorage.getItem(KEY)||"null")||structuredClone(blank);
const $=id=>document.getElementById(id),save=()=>localStorage.setItem(KEY,JSON.stringify(state)),esc=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
$("markBureau").innerHTML=reportingAgencies.map(([value,label])=>`<option value="${value}">${label}</option>`).join("");
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
function renderAll(){renderScores();renderOverview();renderProfile();renderMarks()}
$("insuranceScore").onchange=()=>{state.insurance=$("insuranceScore").value;save()};
$("saveProfile").onclick=()=>{for(const id of ["preferredName","state","city","reviewDate","facts"])state.profile[id]=$(id).value.trim();save();renderAll()};
$("addMark").onclick=()=>{const accuracy=document.querySelector('input[name="accuracy"]:checked')?.value;if(!$("markCreditor").value.trim()||!accuracy)return alert("Enter the report item and answer the accuracy question.");state.marks.push({bureau:$("markBureau").value,creditor:$("markCreditor").value.trim(),type:$("markType").value,date:$("markDate").value,reported:$("reported").value.trim(),evidenceFacts:$("evidenceFacts").value.trim(),accuracy,reason:$("reason").value.trim(),documents:$("documents").value.split("\n").map(v=>v.trim()).filter(Boolean),projectLow:$("projectLow").value,projectHigh:$("projectHigh").value,projectSource:$("projectSource").value.trim()});save();["markCreditor","markDate","reported","evidenceFacts","reason","documents","projectLow","projectHigh","projectSource"].forEach(id=>$(id).value="");document.querySelectorAll('input[name="accuracy"]').forEach(r=>r.checked=false);renderAll()};
function download(name,data){const blob=new Blob([JSON.stringify(data,null,2)],{type:"application/json"}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=name;a.click();URL.revokeObjectURL(a.href)}
$("downloadPlan").onclick=()=>{const disputes=state.marks.filter(m=>m.accuracy==="yes"&&m.reason).map(m=>({bureau:m.bureau.toLowerCase().replace(/[^a-z0-9]/g,""),matchText:m.creditor,reason:m.reason,explanation:`Reported: ${m.reported}\nCorrect facts: ${m.evidenceFacts}`,documents:m.documents}));if(!disputes.length)return alert("No marks qualify. Answer Yes and provide a factual reason first.");download("disputes.json",{disputes})};
$("downloadBackup").onclick=()=>download("credit-report-studio-backup.json",state);
$("eraseData").onclick=()=>{if(confirm("Erase all locally stored profile, score, and mark data?")){localStorage.removeItem(KEY);state=structuredClone(blank);renderAll()}};
renderAll();
