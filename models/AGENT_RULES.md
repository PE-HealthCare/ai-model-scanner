# models — UNTRUSTED INTAKE DROP ZONE

## 1. OWNERSHIP & SCOPE
- **Owner:** P1 (intake boundary enforcement)
- **Purpose:** Secure drop zone for untrusted .safetensors files; NEVER execute contents
- **Allowed Files:** Only .safetensors model weight files
- **FORBIDDEN FILES:** Any .py, .sh, executable, config, or non-model file

## 2. HARD STOP CONDITIONS (MANDATORY)
Agent MUST HALT and report BLOCKED if ANY of these are true:
- ANY attempt to import, execute, or eval model file contents -> IMMEDIATE HALT
- Non-.safetensors file detected -> REJECT + REPORT
- File exceeds approved size limit
- Header parsing fails bounded validation
- Unknown/unrecognized architecture declared
- Agent tries to load model into memory outside safetensors.safe_open

## 3. INPUT CONTRACT
- **Source:** External uploader / test fixture ONLY
- **Trust Level:** ZERO TRUST - treat as adversarial input
- **Validation:** Bounded header parse + architecture compatibility check BEFORE any processing

## 4. OUTPUT CONTRACT
- **Produced:** Trusted graph metadata (input_domain, is_quantized, layer_count) via analyzer.py
- **Security Tag:** All outputs tagged with intake_validation_result = PASS/FAIL/BLOCKED

## 5. SECURITY BOUNDARIES
- USE safetensors.safe_open EXCLUSIVELY - NO pickle, NO torch.load, NO custom loaders
- Bounded header parsing: max_header_bytes=1MB, max_metadata_size=10MB, max_tensor_count=10000
- Reject malformed headers, invalid offsets, pathological dimensions immediately
- NO network access during intake

## 6. WHEN THIS FOLDER IS USED IN PIPELINE
- **Phase:** 02 Zero-Trust Intake (primary); 03+ (reference only)
- **Trigger:** New model file placed in folder
- **Consumed By:** src/p1_static_engine/analyzer.py ONLY
- **Lifecycle:** File remains unmodified; only metadata extracted
