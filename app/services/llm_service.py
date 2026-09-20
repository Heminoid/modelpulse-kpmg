import httpx
from loguru import logger
import json

from app.schemas.insights import InsightContext, LLMConfig, LLMProvider

from app.core.config import settings



class LLMService:
    """Provides LLM-generated narrative summaries for ModelPulse runs."""

    async def generate_narrative(
        self,
        context: InsightContext,
        mode: str = "executive",
        config: LLMConfig = LLMConfig(),
        section: str | None = None,
        existing_narrative: dict | None = None
    ) -> dict:
        """
        Generates a narrative summary from the provided InsightContext.
        Falls back to a deterministic mock narrative if the LLM call fails.
        """
        provider = config.provider
        if provider == "auto" or getattr(settings, "llm_provider", "") == "auto":
            if settings.cloudflare_account_id and settings.cloudflare_api_token:
                provider = LLMProvider.CLOUDFLARE
            else:
                provider = LLMProvider.MOCK

        # A section-scoped regeneration only makes sense if there's an existing
        # narrative to merge the regenerated section into. Otherwise (first-ever
        # generation for this run) fall back to generating the full narrative,
        # so callers never end up persisting a narrative missing the other keys.
        effective_section = section if existing_narrative else None

        if provider == LLMProvider.MOCK:
            result = self._mock_narrative(context, mode)
        elif provider == LLMProvider.CLOUDFLARE:
            if not settings.cloudflare_account_id or not settings.cloudflare_api_token:
                logger.warning("Cloudflare credentials missing. Falling back to mock narrative.")
                result = self._mock_narrative(context, mode)
            else:
                try:
                    result = await self._cloudflare_narrative(context, config, effective_section)
                except Exception as e:
                    logger.error(f"Cloudflare AI call failed: {e}. Falling back to mock.")
                    result = self._mock_narrative(context, mode)
        else:
            raise NotImplementedError(f"Provider {provider} not implemented.")

        if effective_section and existing_narrative:
            merged = dict(existing_narrative)
            merged[effective_section] = result.get(effective_section, result.get('content', ''))
            return merged
        return result

    async def _cloudflare_narrative(self, context: InsightContext, config: LLMConfig, section: str | None = None) -> dict:
        """Calls the Cloudflare Workers AI Llama model to generate the narrative."""
        logger.info(f"Calling Cloudflare Workers AI ({config.model}) for run {context.run_id}")
        
        system_prompt = (
            "You are a Senior Quantitative Analyst at a Big 4 consulting firm specializing in Model Risk Management (MRM). "
            "Your task is to conduct an in-depth, rigorous review of a credit model's performance and stability. "
            "Write a highly detailed, professional analysis that includes specific numbers, percentages, and statistics derived "
            "from the provided context. Speak directly to senior risk executives. Do NOT hallucinate metrics, but DO "
            "extrapolate meaningful insights and quantify risks based strictly on the provided data."
        )

        user_prompt = f"""
        Please write a JSON response with the following exact keys based on the context:
        - "executive_summary": A rigorous, high-level summary of the model's health. Cite specific finding counts and the most critical metric values. (MUST BE A PLAIN STRING, NOT AN OBJECT OR DICT).
        - "technical_summary": An in-depth paragraph detailing specific metric breaches, performance degradation (e.g., AUC, Gini drops), data drift, or calibration issues. Use specific numbers. (MUST BE A PLAIN STRING, NOT AN OBJECT).
        - "root_causes": A bulleted list of strings describing likely quantitative or qualitative root causes based on the findings.
        - "recommended_actions": A bulleted list of actionable MRM recommendations (e.g., "Recalibrate scorecard", "Investigate feature X drift").

        Context:
        Dataset Rows: {context.dataset_rows}
        Has Baseline: {context.has_baseline}
        Findings Count: {json.dumps(context.finding_count_by_severity)}
        Top Worsening Metrics: {', '.join(context.top_worsening_metrics) if context.top_worsening_metrics else 'None'}
        
        Detailed Findings (Use these numbers in your analysis!):
        {json.dumps([f.model_dump() for f in context.deterministic_findings], indent=2)}
        
        Output ONLY valid JSON matching the requested keys, with no additional text or markdown formatting. NEVER NEST JSON OBJECTS INSIDE executive_summary OR technical_summary.
        """
        
        if section:
            section_prompts = {
                'executive_summary': 'Write ONLY the "executive_summary" — a rigorous, high-level summary of the model\'s health. Cite specific finding counts and the most critical metric values. (MUST BE A PLAIN STRING, NOT AN OBJECT OR DICT).',
                'technical_summary': 'Write ONLY the "technical_summary" — an in-depth paragraph detailing specific metric breaches, performance degradation (e.g., AUC, Gini drops), data drift, or calibration issues. Use specific numbers. (MUST BE A PLAIN STRING, NOT AN OBJECT).',
                'root_causes': 'Write ONLY the "root_causes" — a bulleted list of strings describing likely quantitative or qualitative root causes based on the findings.',
                'recommended_actions': 'Write ONLY the "recommended_actions" — a bulleted list of actionable MRM recommendations (e.g., "Recalibrate scorecard", "Investigate feature X drift").'
            }
            
            section_req = section_prompts.get(section, f'Write ONLY the "{section}".')
            user_prompt = f"""
            Please write a JSON response with the following exact key based on the context:
            - "{section}": {section_req}
            
            Context:
            Dataset Rows: {context.dataset_rows}
            Has Baseline: {context.has_baseline}
            Findings Count: {json.dumps(context.finding_count_by_severity)}
            Top Worsening Metrics: {', '.join(context.top_worsening_metrics) if context.top_worsening_metrics else 'None'}
            
            Detailed Findings (Use these numbers in your analysis!):
            {json.dumps([f.model_dump() for f in context.deterministic_findings], indent=2)}
            
            Output ONLY valid JSON matching the requested key, with no additional text or markdown formatting.
            """

        inputs = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        payload = {
            "messages": inputs,
            "max_tokens": 2000
        }
        
        api_base_url = f"https://api.cloudflare.com/client/v4/accounts/{settings.cloudflare_account_id}/ai/run/"
        headers = {"Authorization": f"Bearer {settings.cloudflare_api_token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_base_url}{config.model}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            if not result.get("success"):
                raise ValueError(f"API Error: {result.get('errors')}")
                
            response_text = result["result"].get("response")
            
            if isinstance(response_text, dict):
                parsed_narrative = response_text
                parsed_narrative.setdefault("confidence_notes", []).append("Generated by Cloudflare Workers AI")
                parsed_narrative["generated_by"] = "cloudflare_llm"
                return parsed_narrative
            
            # Try to parse the JSON output from the LLM
            import re
            try:
                # Find the first { and last } to extract pure JSON, bypassing any markdown
                text = str(response_text).strip()
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    json_str = match.group(0)
                else:
                    json_str = text
                
                parsed_narrative = json.loads(json_str)
                
                # If LLM nested the response inside 'executive_summary' by mistake, flatten it gracefully
                def flatten_dict_to_string(d):
                    if not isinstance(d, dict): return str(d)
                    return "\n".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in d.items()])
                
                if isinstance(parsed_narrative.get('executive_summary'), dict):
                    parsed_narrative['executive_summary'] = flatten_dict_to_string(parsed_narrative['executive_summary'])
                if isinstance(parsed_narrative.get('technical_summary'), dict):
                    parsed_narrative['technical_summary'] = flatten_dict_to_string(parsed_narrative['technical_summary'])

                parsed_narrative.setdefault("confidence_notes", []).append("Generated by Cloudflare Workers AI")
                parsed_narrative["generated_by"] = "cloudflare_llm"
                return parsed_narrative
            except json.JSONDecodeError as e:
                logger.warning(f"Could not parse LLM response as JSON: {e}")
                return {
                    "executive_summary": "LLM failed to produce valid JSON. Raw output below:\n\n" + str(response_text),
                    "technical_summary": "Failed to parse structured JSON from LLM.",
                    "root_causes": [],
                    "recommended_actions": [],
                    "confidence_notes": ["Generated by Cloudflare Workers AI (Llama 3), but format was invalid."],
                    "generated_by": "cloudflare_llm_raw",
                }


    def _mock_narrative(self, context: InsightContext, mode: str) -> dict:
        """Generate a deterministic mock narrative from findings."""
        # Build from findings and metric status — no hallucination
        crit = context.finding_count_by_severity.get("critical", 0)
        warn = context.finding_count_by_severity.get("warning", 0)
        
        if crit > 0:
            exec_summary = f"The model is in a critical state with {crit} critical issues detected."
        elif warn > 0:
            exec_summary = f"The model is deteriorating with {warn} warnings."
        else:
            exec_summary = "The model is healthy and stable."

        return {
            "executive_summary": exec_summary,
            "technical_summary": "Mock technical summary based on findings.",
            "root_causes": ["Mock cause 1", "Mock cause 2"],
            "key_segments": [s.get("value", "") for s in context.top_worsening_segments[:3]],
            "recommended_actions": ["Mock action 1"],
            "confidence_notes": ["Generated deterministically from computed metrics. No LLM used."],
            "generated_by": "mock_deterministic",
        }

    async def generate_comparison_narrative(
        self,
        champion_metrics: dict,
        challenger_metrics: dict,
        deltas: dict,
        winners: dict,
        config: LLMConfig = LLMConfig()
    ) -> dict:
        """Generate AI narrative comparing champion vs challenger models."""
        provider = config.provider
        if provider == "auto" or getattr(settings, "llm_provider", "") == "auto":
            if settings.cloudflare_account_id and settings.cloudflare_api_token:
                provider = LLMProvider.CLOUDFLARE
            else:
                provider = LLMProvider.MOCK
        
        if provider == LLMProvider.MOCK or not settings.cloudflare_account_id or not settings.cloudflare_api_token:
            return self._mock_comparison(champion_metrics, challenger_metrics, deltas, winners)
        
        try:
            # Build comparison prompt
            system_prompt = (
                "You are a Senior Quantitative Analyst comparing two credit scoring models. "
                "Provide a clear, data-driven comparison for senior risk executives."
            )
            
            comparison_data = []
            for key in deltas:
                comparison_data.append(f"- {key}: Champion={champion_metrics.get(key, 'N/A')}, "
                                       f"Challenger={challenger_metrics.get(key, 'N/A')}, "
                                       f"Delta={deltas[key]:+.4f}, Winner={winners.get(key, 'tie')}")
            
            user_prompt = f"""Compare these two models and provide a JSON response with:
            - "comparison_summary": A professional paragraph comparing the models' performance (string)
            - "key_differences": List of the most important differences
            - "recommendation": Your recommendation on whether to promote the challenger
            - "risks": Any risks of promoting the challenger
            
            Metric Comparison:
            {chr(10).join(comparison_data)}
            
            Output ONLY valid JSON."""
            
            inputs = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
            payload = {"messages": inputs, "max_tokens": 1500}
            
            api_base_url = f"https://api.cloudflare.com/client/v4/accounts/{settings.cloudflare_account_id}/ai/run/"
            headers = {"Authorization": f"Bearer {settings.cloudflare_api_token}"}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{api_base_url}{config.model}", headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
                response_text = result["result"].get("response", "")
                
                import re
                text = str(response_text).strip()
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    parsed["generated_by"] = "cloudflare_llm"
                    return parsed
                return self._mock_comparison(champion_metrics, challenger_metrics, deltas, winners)
        except Exception as e:
            logger.error(f"Champion/Challenger narrative failed: {e}")
            return self._mock_comparison(champion_metrics, challenger_metrics, deltas, winners)

    def _mock_comparison(self, champ_metrics, chall_metrics, deltas, winners):
        chall_wins = list(winners.values()).count('challenger')
        champ_wins = list(winners.values()).count('champion')
        
        key_diffs = []
        for key, winner in winners.items():
            delta = deltas.get(key, 0)
            key_diffs.append(f"{key}: {'Challenger' if winner == 'challenger' else 'Champion'} is better by {abs(delta):.4f}")
        
        return {
            'comparison_summary': f'The challenger model won on {chall_wins} metrics while the champion retained superiority on {champ_wins} metrics.',
            'key_differences': key_diffs[:5],
            'recommendation': 'Consider promoting the challenger' if chall_wins > champ_wins else 'Champion should be retained',
            'risks': ['Score distribution may shift post-deployment', 'Recalibration may be needed'],
            'generated_by': 'mock_deterministic'
        }
