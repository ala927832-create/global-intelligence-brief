"""One-call, free-tier-only Gemini model probe. Never prints secrets or API body."""
import json
import os
import sys
import requests

MODEL="gemini-3.5-flash-lite"
BASE="https://generativelanguage.googleapis.com/v1beta"
def run():
    if os.getenv("GEMINI_FREE_TIER_CONFIRMED")!="1" or os.getenv("ENABLE_ONE_CALL_PROBE")!="1":
        return {"status":"LOCKED","model":MODEL,"model_call_count":0}
    key=os.getenv("GEMINI_API_KEY","")
    if not key:
        return {"status":"NO_KEY","model":MODEL,"model_call_count":0}
    header={"x-goog-api-key":key}
    result={"model":MODEL,"model_call_count":0,"stage":"MODEL_LOOKUP"}
    try:
        check=requests.get(f"{BASE}/models/{MODEL}",headers=header,timeout=15)
        result["model_http_status"]=check.status_code
        if check.status_code!=200:
            result["status"]="MODEL_LOOKUP_FAILED"
            return result
        model=check.json()
        result["supports_generate_content"]="generateContent" in model.get("supportedGenerationMethods",[])
        if not result["supports_generate_content"]:
            result["status"]="GENERATE_NOT_LISTED"
            return result
        result["stage"]="ONE_MINIMAL_GENERATION"
        # One request, no retry. No grounding, tools, uploads, private data, or lengthy prompts.
        payload={"contents":[{"parts":[{"text":"請只回覆：測試成功"}]}],
                 "generationConfig":{"temperature":0,"maxOutputTokens":128}}
        result["model_call_count"]=1
        response=requests.post(f"{BASE}/models/{MODEL}:generateContent",
             headers={**header,"Content-Type":"application/json"},
             json=payload,timeout=35)
        result["generate_http_status"]=response.status_code
        if response.status_code!=200:
            result["status"]="GENERATION_HTTP_ERROR"
            return result
        body=response.json()
        parts=[part.get("text","") for c in body.get("candidates",[])
               for part in c.get("content",{}).get("parts",[])]
        response_text="".join(parts).strip()
        result["has_nonempty_response"]=bool(response_text)
        usage=body.get("usageMetadata") or {}
        result["usage_tokens"]={k:usage.get(k) for k in
            ("promptTokenCount","candidatesTokenCount","totalTokenCount") if k in usage}
        result["status"]="SUCCEEDED" if response_text else "EMPTY_RESPONSE"
        return result
    except (requests.RequestException,ValueError,KeyError):
        result["status"]="TRANSPORT_OR_FORMAT_ERROR"
        return result

if __name__=="__main__":
    outcome=run()
    print(json.dumps(outcome,ensure_ascii=False))
    summary=os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as f:
            f.write("## Gemini 免費層模型單次診斷（不發布）\n\n")
            f.write("模型："+outcome.get("model","")+"；狀態："+outcome["status"]+
                 "；最多一次生成；金鑰與 API 回應內容均未記錄。\n\n")
            for field in ("model_http_status","generate_http_status","model_call_count","usage_tokens"):
                if field in outcome:f.write("- "+field+"："+str(outcome[field])+"\n")
            f.write("\n模型 GET 不證明計費方案，免費層須由專案擁有人在 AI Studio 確認。\n")
    sys.exit(0 if outcome["status"]=="SUCCEEDED" else 2)
