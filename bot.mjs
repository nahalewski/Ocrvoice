import { chromium } from "playwright";
import { access, mkdir, readFile } from "node:fs/promises";
import { createInterface } from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";
import { resolve } from "node:path";

const BUREAUS = {
  experian: { name: "Experian", url: "https://www.experian.com/help/dispute-credit/", channel: "portal" },
  transunion: { name: "TransUnion", url: "https://dispute.transunion.com/", channel: "portal" },
  equifax: { name: "Equifax", url: "https://my.equifax.com/", channel: "portal" },
  innovis: { name: "Innovis", url: "https://www.innovis.com/personal/disputeResolution", channel: "portal" },
  lexisnexis: { name: "LexisNexis Risk Solutions", url: "https://consumer.risk.lexisnexis.com/contact", channel: "assisted" },
  chexsystems: { name: "ChexSystems", url: "https://www.chexsystems.com/dispute", channel: "portal" },
  earlywarning: { name: "Early Warning Services", url: "https://www.earlywarning.com/dispute-file-disclosure", channel: "document" },
  clarityservices: { name: "Experian Clarity Services", url: "https://consumers.clarityservices.com/", channel: "assisted" },
  datax: { name: "DataX", url: "https://consumers.dataxltd.com/", channel: "document" },
  corelogicteletrack: { name: "Teletrack (now DataX)", url: "https://consumers.teletrack.com/", channel: "document" },
  nctue: { name: "NCTUE", url: "https://www.nctue.com/", channel: "assisted" },
};
const profilePath = resolve(".browser-profile");
const outputPath = resolve("output");
const planPath = resolve(process.argv[2] || "disputes.json");
const rl = createInterface({ input, output });

function stop(message) {
  throw new Error(message);
}

async function loadPlan() {
  try {
    const plan = JSON.parse(await readFile(planPath, "utf8"));
    if (!Array.isArray(plan.disputes) || plan.disputes.length === 0) stop("The plan must contain at least one dispute.");
    for (const [index, item] of plan.disputes.entries()) {
      item.bureau = String(item.bureau || "experian").toLowerCase();
      if (!BUREAUS[item.bureau]) stop(`Dispute ${index + 1} has an unsupported bureau.`);
      if (!item.matchText || !item.reason || !item.explanation) stop(`Dispute ${index + 1} needs matchText, reason, and explanation.`);
      if (item.explanation.length > 1000) stop(`Dispute ${index + 1} explanation is over 1,000 characters.`);
      for (const document of item.documents || []) await access(resolve(document));
    }
    return plan;
  } catch (error) {
    if (error.code === "ENOENT") stop("Create disputes.json from disputes.example.json first.");
    throw error;
  }
}

async function chooseCandidate(page, item) {
  const candidates = page.getByText(item.matchText, { exact: false });
  const count = await candidates.count();
  if (count === 0) {
    console.log(`\nCould not find “${item.matchText}” on this page.`);
    console.log("Navigate to that account or report item in the browser.");
    await rl.question("Press Enter once the item is visible… ");
    return;
  }
  if (count === 1) {
    await candidates.click();
    await page.waitForTimeout(800);
    return;
  }
  console.log(`\nFound ${count} matches for “${item.matchText}”. Open the correct item manually.`);
  await rl.question("Press Enter after opening the correct item… ");
}

async function clickDisputeAction(page) {
  const actions = page.getByRole("button").or(page.getByRole("link"));
  const count = await actions.count();
  const matches = [];
  for (let index = 0; index < Math.min(count, 100); index += 1) {
    const control = actions.nth(index);
    const text = (await control.innerText().catch(() => "")).trim();
    if (/dispute|incorrect|report an error/i.test(text)) matches.push({ control, text });
  }
  if (matches.length === 1) {
    console.log(`Opening: ${matches[0].text}`);
    await matches[0].control.click();
    await page.waitForTimeout(800);
    return;
  }
  if (matches.length > 1) console.log("Possible dispute actions:", matches.map((match) => match.text));
  console.log("Click the correct Start Dispute action in the browser.");
  await rl.question("Press Enter when the dispute form is open… ");
}

async function selectReason(page, reason) {
  const selects = page.locator("select");
  const count = await selects.count();
  for (let index = 0; index < count; index += 1) {
    const select = selects.nth(index);
    const options = await select.locator("option").allTextContents();
    const match = options.find((option) => option.trim().toLowerCase() === reason.trim().toLowerCase())
      || options.find((option) => option.toLowerCase().includes(reason.toLowerCase()));
    if (match) {
      await select.selectOption({ label: match });
      return true;
    }
  }
  return false;
}

async function fillExplanation(page, explanation) {
  const textareas = page.locator("textarea:visible");
  if (await textareas.count() === 1) {
    await textareas.fill(explanation);
    return true;
  }
  const labeled = page.getByLabel(/explain|details|tell us more|comment/i);
  if (await labeled.count() === 1) {
    await labeled.fill(explanation);
    return true;
  }
  return false;
}

async function uploadDocuments(page, documents) {
  if (!documents?.length) return true;
  const upload = page.locator('input[type="file"]');
  if (await upload.count() !== 1) return false;
  await upload.setInputFiles(documents.map((document) => resolve(document)));
  return true;
}

async function prepareDispute(page, item, index) {
  console.log(`\nPreparing dispute ${index + 1}: ${item.matchText}`);
  await chooseCandidate(page, item);
  await clickDisputeAction(page);

  if (!(await selectReason(page, item.reason))) {
    console.log(`Select this reason manually: ${item.reason}`);
    await rl.question("Press Enter after selecting it… ");
  }
  if (!(await fillExplanation(page, item.explanation))) {
    console.log("The explanation box was not uniquely identifiable. Paste this text manually:\n");
    console.log(item.explanation);
    await rl.question("Press Enter after filling it… ");
  }
  if (!(await uploadDocuments(page, item.documents || []))) {
    console.log("Upload these supporting files manually:", item.documents);
    await rl.question("Press Enter after uploading them… ");
  }

  await page.screenshot({ path: resolve(outputPath, `dispute-${index + 1}-review.png`), fullPage: true });
  console.log("Prepared. Review every field in the browser.");
  console.log("The copilot will not click Submit or make an attestation for you.");
  await rl.question("After reviewing, submit manually or cancel. Press Enter to continue… ");
}

async function prepareNonPortalDispute(page, item, index, bureau) {
  console.log(`\nPreparing ${bureau.name} dispute ${index + 1}: ${item.matchText}`);
  console.log(bureau.channel === "document"
    ? "This agency currently uses a form, secure document transfer, or mail workflow."
    : "This agency requires consumer-support assistance or has no stable dispute form for safe automation.");
  console.log(`Item: ${item.matchText}`);
  console.log(`Reason: ${item.reason}`);
  console.log(`Explanation: ${item.explanation}`);
  if (item.documents?.length) console.log("Documents:", item.documents.map((document) => resolve(document)));
  await page.screenshot({ path: resolve(outputPath, `dispute-${index + 1}-${item.bureau}-channel.png`), fullPage: true });
  console.log("The copilot will not send mail, attest, or submit this dispute for you.");
  await rl.question("Complete and review the agency's supported process, then press Enter to continue… ");
}

async function main() {
  const plan = await loadPlan();
  await mkdir(profilePath, { recursive: true });
  await mkdir(outputPath, { recursive: true });
  const context = await chromium.launchPersistentContext(profilePath, {
    headless: false,
    viewport: null,
    args: ["--start-maximized"],
  });
  const pages = context.pages();
  const page = pages[0] || await context.newPage();
  console.log("Do not enter passwords, SSNs, or security answers in this terminal.");
  for (const bureauKey of Object.keys(BUREAUS)) {
    const items = plan.disputes.map((item, index) => ({ item, index })).filter(({ item }) => item.bureau === bureauKey);
    if (!items.length) continue;
    const bureau = BUREAUS[bureauKey];
    await page.goto(bureau.url, { waitUntil: "domcontentloaded" });
    if (bureau.channel === "portal") {
      console.log(`\nLog in to ${bureau.name} manually in the browser.`);
      await rl.question(`Navigate to your current ${bureau.name} report, then press Enter here… `);
      for (const { item, index } of items) await prepareDispute(page, item, index);
    } else {
      console.log(`\n${bureau.name} does not have a stable online dispute form that this copilot can safely fill.`);
      for (const { item, index } of items) await prepareNonPortalDispute(page, item, index, bureau);
    }
  }
  console.log("\nFinished preparing the listed disputes. The browser remains open for your review.");
  await rl.question("Press Enter to close the browser… ");
  await context.close();
}

main().catch((error) => {
  console.error(`\nStopped: ${error.message}`);
  process.exitCode = 1;
}).finally(() => rl.close());
