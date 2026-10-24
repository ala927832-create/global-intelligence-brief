"""Read-only Gemini model metadata for a confirmed Free Tier project.

No generateContent calls, retries, tool invocation or charged traffic.
Model existence is NOT a guarantee of free quota; check AI Studio limits.
"""
import json
import os
import requests
MODELS=("gemini-3.8-flash","gemini-3.6-flash","gemini-3.5-flash-lite","gemini-3.1-pro-preview")
URL="https://generativelanguage.googleapis.com/v1beta/models/{}"

def read_catalog(get=requests.get):
    if os.getenv("GEMINI_FREE_TIER_CONFIRMED")!="1":
        return {"status":"LOCKED","message":"Free project not confirmed","model_calls":0,"models":[]}
    key=os.getenv("GEMINI_API_KEY","")
    if not key:
        return {"status":"NO_KEY","model_calls":0,"models":[]}
    result=[]
    for mid in MODELS:
        try:
            res=get(URL.format(mid),headers={"x-goog-api-key":key},timeout=12)
            if res.status_code==200:
                data=res.json()
                result.append({"model":mid,"status":200,
                    "supports_generate_content":"generateContent" in data.get("supportedGenerationMethods",[]),
                    "input_token_limit":data.get("inputTokenLimit"),
                    "output_token_limit":data.get("outputTokenLimit")})
            else:
                result.append({"model":mid,"status":res.status_code})
        except (requests.RequestException,ValueError):
            result.append({"model":mid,"status":"TRANSPORT_ERROR"})
    return {"status":"METADATA_CHECK_DONE","model_calls":0,"models":result,
            "warning":"Access does not establish actual free RPM/TPM/RPD; confirm Google AI Studio before switching."}

if __name__=="__main__":
    result=read_catalog()
    print(json.dumps(result,ensure_ascii=False))
    path=os.getenv("GITHUB_STEP_SUMMARY")
    if path:
        with open(path,"a",encoding="utf-8") as f:
            f.write("## Gemini model metadata (0 model generation calls)\n\n")
            for model in result["models"]:
                f.write(f"- {model['model']} : {model.get('status')} / generateContent={model.get('supports_generate_content','unknown')}\n")
            f.write("\nOnly the owner can confirm project-specific free quotas in AI Studio. Never enable a paid fallback.\n")
