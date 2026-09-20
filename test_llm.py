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

    # Calls the real service method, which reads credentials from
    # app.core.config.settings (backed by .env) — never hardcode them here.
    original_cf = svc._cloudflare_narrative

    try:
        res = await original_cf(ctx, config)
        print("Result:", res)
    except Exception as e:
        print("EXCEPTION TYPE:", type(e))
        import traceback
        traceback.print_exc()

asyncio.run(test())
