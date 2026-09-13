# CUMCM 2026 project instructions

- Use the Sustainable-Enjoyment template, pinned in vendor/sustainable-enjoyment. Preserve its typography. Root cumcmthesis.cls only adds font fallbacks; do not load the legacy `archive/legacy-template-files/cumcm2026.sty`.
- Maintain only the electronic submission entry in `main.tex`. If a paper submission is requested later, create a separate entry and use the official 2026 commitment and numbering pages.
- Content structure may follow the problem. The files in contents/ are conveniences, not mandatory chapters or an official requirement.
- Official 2026 format and AI rules take precedence over skill defaults; see docs/template-reference.md. No mandated font, font size, line spacing, abstract word count or minimum paper length. Appendices must contain complete runnable source code, not only selected excerpts.
- preview.tex is a layout demonstration, never competition evidence or a submission. Keep its sample content separate from main.tex.
- Put reproducible plotting scripts in `scripts/plotting/` and final figures in `figures/final/`.
- Never invent numerical results, citations, experiments, or model performance. Every quantitative claim must trace to `results/`, `data/`, or executable code.
- Keep competition inputs in `data/` unchanged. Derived files belong in `results/`.
- Compile with `latexmk main.tex` and inspect `build/main.pdf` before declaring paper changes complete.
- Maintain the AI-use declaration according to actual usage, and check all outputs for identity information before submission.
- For drafting, revising, or reviewing the abstract and paper body, use the repository skill `cumcm-excellent-paper-writing` and its project quality rubric.
- Treat excellent papers only as evidence about organization and exposition: never copy distinctive wording, numerical results, conclusions, or figures, and never use them as substitutes for research citations.
- Before substantial section writing, identify the argument chain and evidence files; after authorized drafting or revision, rescore the section and revise every writing dimension below 4/5.
