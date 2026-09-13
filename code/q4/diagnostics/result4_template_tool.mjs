import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const here = path.dirname(fileURLToPath(import.meta.url));
const q4Dir = path.dirname(here);
const workDir = path.dirname(q4Dir);
const inRepositoryLayout = path.basename(q4Dir).toLowerCase() === "q4"
  && path.basename(path.dirname(q4Dir)).toLowerCase() === "code";
const repositoryRoot = inRepositoryLayout ? path.dirname(path.dirname(q4Dir)) : null;
const diagnosticOutputDir = inRepositoryLayout
  ? path.join(repositoryRoot, "results", "q4", "diagnostics")
  : here;
const templateCandidates = inRepositoryLayout
  ? [path.join(repositoryRoot, "data", "raw", "problems", "A题", "附件", "附件3", "result4.xlsx")]
  : [
      path.join(workDir, "CUMCM2026Problems", "A题", "附件", "附件3", "result4.xlsx"),
      path.join(path.dirname(workDir), "cumcm-2026", "data", "raw", "problems", "A题", "附件", "附件3", "result4.xlsx"),
    ];
let templatePath = null;
for (const candidate of templateCandidates) {
  try {
    await fs.access(candidate);
    templatePath = candidate;
    break;
  } catch {}
}
if (!templatePath) throw new Error("找不到官方result4.xlsx模板");

const mode = process.argv[2] ?? "audit";
const input = await FileBlob.load(templatePath);
const workbook = await SpreadsheetFile.importXlsx(input);
const overview = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 6000,
  tableMaxRows: 8,
  tableMaxCols: 24,
});
process.stdout.write(`${overview.ndjson}\n`);
const sheet = workbook.worksheets.getItemAt(0);

if (mode === "audit") {
  await fs.mkdir(path.join(diagnosticOutputDir, "input_audit"), { recursive: true });
  const preview = await workbook.render({
    sheetName: sheet.name,
    range: "A1:F5",
    scale: 2,
    format: "png",
  });
  await fs.writeFile(
    path.join(diagnosticOutputDir, "input_audit", "result4_template.png"),
    new Uint8Array(await preview.arrayBuffer()),
  );
  process.exit(0);
}

if (mode !== "build") throw new Error(`未知模式：${mode}`);
const payload = JSON.parse(
  await fs.readFile(
    inRepositoryLayout
      ? path.join(repositoryRoot, "results", "q4", "result4_payload.json")
      : path.join(q4Dir, "result4_payload.json"),
    "utf8",
  ),
);
await fs.mkdir(diagnosticOutputDir, { recursive: true });
const rowCount = payload.rows.length + 1;
if (payload.headers.length !== 22) throw new Error("载荷表头必须为22列");
if (payload.rows.some((row) => row.length !== 22)) throw new Error("载荷数据行必须为22列");

// 以官方模板现有单元格为样式源，仅把占位布局扩展为完整数据区。
sheet.getRange(`B1:U1`).copyFrom(sheet.getRange("B1"), "all");
sheet.getRange("V1").copyFrom(sheet.getRange("F1"), "all");
sheet.getRange(`A2:A${rowCount}`).copyFrom(sheet.getRange("A2"), "all");
sheet.getRange(`B2:V${rowCount}`).copyFrom(sheet.getRange("B2"), "all");
sheet.getRange("A1:V1").values = [payload.headers];
sheet.getRange(`A2:V${rowCount}`).values = payload.rows;
sheet.getRange(`B2:V${rowCount}`).format.numberFormat = payload.number_format;
workbook.recalculate();

const topCheck = await workbook.inspect({
  kind: "table",
  range: "Sheet1!A1:V8",
  include: "values,formulas",
  tableMaxRows: 8,
  tableMaxCols: 22,
});
process.stdout.write(`${topCheck.ndjson}\n`);
const errorCheck = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  summary: "result4 formula error scan",
});
process.stdout.write(`${errorCheck.ndjson}\n`);

const topPreview = await workbook.render({
  sheetName: sheet.name,
  range: "A1:V12",
  scale: 1.5,
  format: "png",
});
await fs.writeFile(
  path.join(diagnosticOutputDir, "result4_preview_top.png"),
  new Uint8Array(await topPreview.arrayBuffer()),
);
const bottomPreview = await workbook.render({
  sheetName: sheet.name,
  range: `A${Math.max(1, rowCount - 5)}:V${rowCount}`,
  scale: 1.5,
  format: "png",
});
await fs.writeFile(
  path.join(diagnosticOutputDir, "result4_preview_bottom.png"),
  new Uint8Array(await bottomPreview.arrayBuffer()),
);

const output = await SpreadsheetFile.exportXlsx(workbook);
const outputPath = inRepositoryLayout
  ? path.join(repositoryRoot, "tables", "q4", "result4.xlsx")
  : path.join(q4Dir, "result4.xlsx");
await fs.mkdir(path.dirname(outputPath), { recursive: true });
await output.save(outputPath);

const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const savedSheetCheck = await reopened.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 2000,
});
process.stdout.write(`${savedSheetCheck.ndjson}\n`);
const savedTopCheck = await reopened.inspect({
  kind: "table",
  range: "Sheet1!A1:V6",
  include: "values,formulas",
  tableMaxRows: 6,
  tableMaxCols: 22,
  maxChars: 6000,
});
process.stdout.write(`${savedTopCheck.ndjson}\n`);
