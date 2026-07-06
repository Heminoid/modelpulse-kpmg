import asyncio
from app.services.llm_service import LLMService
from app.schemas.insights import InsightContext, LLMConfig

async def test():
    svc = LLMService()
    ctx = InsightContext(
        run_id="test",
        monitor_name="test",
        template_type="test",
        run_date="2023",
        dataset_rows=100,
        has_baseline=False,
        target_base_rate=0.1
    )
    config = LLMConfig(model="@cf/meta/llama-3.1-8b-instruct")
    
    # Temporarily override to print result
    original_cf = svc._cloudflare_narrative
    async def debug_cf(ctx, cfg):
        import httpx
        system_prompt = "You are a bot. Return a JSON object."
        user_prompt = "Do it."
        inputs = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        payload = {"messages": inputs}
        API_BASE_URL = "https://api.cloudflare.com/client/v4/accounts/807138141acff1fd312857bec4c03ed0/ai/run/"
        HEADERS = {"Authorization": "Bearer cfut_aKIwZLQFcG143f0gKG8KoTO92a0JKXXtLanVDtK1dd8ba334"}
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{API_BASE_URL}{cfg.model}", headers=HEADERS, json=payload)
            res = response.json()
            print("CLOUDFLARE RESPONSE:", res)
            response_text = res["result"].get("response")
            print("TYPE response_text:", type(response_text))
            return response_text
    # don't override, just run the original to see exactly where it fails
    
    try:
        res = await original_cf(ctx, config)
        print("Result:", res)
    except Exception as e:
        print("EXCEPTION TYPE:", type(e))
        import traceback
        traceback.print_exc()

asyncio.run(test())
