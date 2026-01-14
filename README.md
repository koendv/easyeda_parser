# EasyEDA Parser – PCB to YAML Converter for AI Circuit Analysis

Convert [EasyEDA Pro](https://pro.easyeda.com/) PCB design data into structured YAML for AI-assisted design review and intent analysis.

---

## Quick Start

- **Install**: `pip install pandas pyyaml tiktoken`
- **Export** from EasyEDA Pro:
    - BOM (XLSX)
    - Pick & Place (XLSX)
    - Netlist (.enet)
- **Run**: `easyeda_parser.py BOM.xlsx PickPlace.xlsx Netlist.enet`
- **Upload** `pcb_analysis.yaml` to your AI

---

## Overview

Traditional PCB tools focus on **DRC** (Design Rule Check) and **DFM** (Design for Manufacturing), such as those in EasyEDA Pro [DRM](https://prodocs.easyeda.com/en/pcb/design-check-drc/) or JLCPCB's [DFM service](https://jlcdfm.com/). This tool serves a different purpose: **circuit intent analysis**.

This tool helps answer questions like:

- What is this circuit designed to do?
- Are the components appropriate for the intended function?
- What design assumptions are present?
- What information is missing or unclear?

Instead of uploading bulky schematics or Gerber files to AI, this tool combines three key exports from EasyEDA Pro:

- **BOM** (What components used)
- **Pick and Place** (Where components are)
- **Netlist** (How components connect)

These are merged into a single [YAML](https://yaml.org/) file optimized for AI processing.

---

## Target Users

PCB designers and engineers using **EasyEDA Pro** who want to:

- Experiment with AI-assisted design review
- Verify component suitability for specific functions
- Document or communicate circuit design intent
- Create lightweight, analysis-ready PCB representations

---

## Scope & Limitations

- Supports **EasyEDA Pro** only
- PCB-level analysis only (no schematic support)
- No electrical simulation or compliance checking
- Intended as a **preprocessor** for AI analysis

---

## Workflow

```
EasyEDA Pro → Export 3 files → easyeda_parser.py → pcb_analysis.yaml → AI analysis
```

---

## Usage

### 1. Export from EasyEDA Pro

**Important**: Use EasyEDA Pro (not Standard edition), and export in these exact formats:

- **BOM**
    - Format: **XLSX** (not CSV)
    - Select all fields under: Statistics, Base Attributes, Key Attributes

- **Pick and Place**
    - Format: **XLSX** (not CSV)

- **Netlist**
    - Format: **EasyEDA Professional (.enet)**

You should get three files: `BOM_XXX.xlsx`, `PickPlace_XXX.xlsx`, `Netlist_XXX.enet`

### 2. Install Dependencies

Install python libraries:

```bash
pip install pandas pyyaml tiktoken
```

On ubuntu/debian:

```bash
sudo apt-get install python3-pandas python3-yaml python3-tiktoken
```

### 3. Generate YAML

```bash
easyeda_parser.py BOM_XXX.xlsx PickPlace_XXX.xlsx Netlist_XXX.enet
```

Output: `pcb_analysis.yaml`

### 4. (Optional) Limit File Size

If the AI truncates large files, limit the number of tokens in `pcb_analysis.yaml`. If the AI context window is 50000 tokens:

```bash
easyeda_parser.py --token-limit 50000 BOM_XXX.xlsx PickPlace_XXX.xlsx Netlist_XXX.enet
```

Electrical connectivity is preserved; less critical details may be reduced.

---

## AI Interaction Examples

After uploading `pcb_analysis.yaml`, ask queries. Below are sample queries:

### What is this circuit designed to do, and what assumptions did the designer make?

Combines purpose analysis with hidden constraint identification

```prompt
Based on the components, layout, and connectivity, what was this circuit designed to do?
What environmental, usage, or performance assumptions are evident in the design choices?
```

### Describe the functional blocks and signal/power flow through the system

System-level analysis for overall understanding

```prompt
Break this circuit down into functional blocks (power, processing, interfaces, etc.).
Trace the signal and power flow between blocks, noting key transformation points.
```

### List key components and evaluate if they're appropriate for their roles

From identification to evaluation

```prompt
Identify the most critical components by function.
For each, explain its role and evaluate if it's appropriately specified for that role
(considering specs, cost, alternatives, and design context).
```

### Analyze the power delivery network: regulation, filtering, and decoupling

Power integrity

```prompt
Map the power delivery network from input to all ICs.
Analyze regulator choices, filter effectiveness, and decoupling capacitor placement/sizing.
Flag any potential issues for different load conditions.
```

### What protection, filtering, and signal integrity measures are implemented?

Robustness and reliability analysis

```prompt
Identify ESD protection, EMI filtering, isolation, and signal conditioning.
Evaluate adequacy for the likely operating environment and interfaces.
```

### Assess according to [standard] with specific measurements

Standards-based compliance check

```prompt
[Example for isolation] Using coordinates from the YAML, measure creepage/clearance distances.
Assess against IEC 60664-1 for 250V working voltage, pollution degree 2.
State all assumptions and measurement methods.
```

---

## Example Projects

Check [examples/](examples/) folder:

- CAN bus interface module
- AT32F405 microcontroller board

These show real output format and typical file size.

---

## Notes for Chinese Users

- Tested with both Chinese and English versions of EasyEDA Pro
- DeepSeek (128K context) works well for large projects

---

## Development Background

This tool was created through AI-assisted development:

- Specification written in `easyeda_parser_spec.yaml`
- Code generated by [DeepSeek](https://www.deepseek.com/)
- Output validated on multiple AI
- Tested with real EasyEDA Pro exports

To modify, upload the following files to an AI:

- `easyeda_parser_spec.yaml`
- `easyeda_parser.py`
- a sample EasyEDA BOM, Pick and Place, and Netlist. Truncate the Netlist to 500 lines to limit size.

Describe required changes. A typical development cycle:

- Upload `easyeda_parser.py`, `easyeda_parser_spec.yaml` and sample project.
- "Do not generate code yet. First discuss."
- State required behavior.
- "Do any questions remain?"
- "Is additional data needed?"
- "What assumptions are made?"
- "Proceed. Generate code."
- Download and test python script.
- "Give me the parser specification yaml."
- Download and save new `easyeda_parser_spec.yaml` file for next session.

---

## Important Notes

**This is an experimental tool.**

- Not for safety-critical decisions
- Always verify with traditional EDA tools
- Engineering review is essential
- No liability for design or manufacturing outcomes

---

## License

Public Domain. No warranty.

---

## Feedback

- GitHub Issues welcome
- Include example files when reporting issues
- Suggestions for YAML structure improvements appreciated
