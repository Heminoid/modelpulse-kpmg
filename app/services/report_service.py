import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
import logging
from typing import Optional
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

from app.schemas.reports import ReportType, ReportFormat
from app.schemas.charts import ChartPayload
from app.charts.renderer import render_to_base64
from app.storage.run_store import MonitorRunStore

class WeasyPrintUnavailableError(Exception):
    pass

class ReportService:
    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))
        
    def generate(self, run_id: str, report_type: ReportType, fmt: ReportFormat, run_store: MonitorRunStore, sections: Optional[list[str]] = None) -> Path:
        run = run_store.get(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
            
        health = run_store.load_artifact(run_id, "health.json") or {}
        metrics = run_store.load_artifact(run_id, "metrics.json") or []
        charts = run_store.load_artifact(run_id, "charts.json") or []
        alerts = run_store.load_artifact(run_id, "alerts.json") or []
        
        # Load all additional insights for the report
        narrative = run_store.load_artifact(run_id, "narratives.json") or {}
        stat_tests = run_store.load_artifact(run_id, "stat_tests.json") or {}
        vintage = run_store.load_artifact(run_id, "vintage.json") or {}
        override = run_store.load_artifact(run_id, "override.json") or {}
        fairness = run_store.load_artifact(run_id, "fairness.json") or {}
        segments = run_store.load_artifact(run_id, "segments.json") or []
        insights = run_store.load_artifact(run_id, "insights.json") or {}
        timeseries = run_store.load_artifact(run_id, "timeseries.json") or {}

        if sections is not None:
            if len(sections) == 0:
                metrics = []
                vintage = {}
                override = {}
                fairness = {}
                charts = []
                stat_tests = {}
                alerts = []
                narrative = {}
                segments = []
                insights = {}
                timeseries = {}
            else:
                category_map = {
                    'performance': ['performance'],
                    'calibration': ['calibration'],
                    'stability': ['drift', 'stability'],
                    'data_quality': ['data_quality'],
                    'delinquency': ['delinquency'],
                    'strategy': ['strategy'],
                }
                allowed_categories = set()
                for s in sections:
                    allowed_categories.update(category_map.get(s, [s]))
                metrics = [m for m in metrics if m.get('category') in allowed_categories]
                if 'vintage' not in sections:
                    vintage = {}
                if 'override' not in sections:
                    override = {}
                if 'fairness' not in sections:
                    fairness = {}
                if 'charts' not in sections:
                    charts = []
                if 'stat_tests' not in sections:
                    stat_tests = {}
                if 'alerts' not in sections:
                    alerts = []
                if 'narrative' not in sections and 'executive_summary' not in sections:
                    narrative = {}
                if 'segments' not in sections:
                    segments = []
                if 'insights' not in sections:
                    insights = {}
                if 'timeseries' not in sections:
                    timeseries = {}

        # Render charts to base64
        chart_images = {}
        for c_dict in charts:
            c = ChartPayload(**c_dict)
            chart_images[c.chart_id] = render_to_base64(c)
            
        template_name = f"reports/{report_type.value}.html"
        try:
            template = self.env.get_template(template_name)
        except Exception:
            template = self.env.get_template("reports/base.html")
            
        # Load logo for templates
        import base64
        logo_path = Path(__file__).parent.parent / "static" / "kpmg-logo.png"
        kpmg_logo_b64 = ""
        if logo_path.exists():
            with open(logo_path, "rb") as f:
                kpmg_logo_b64 = base64.b64encode(f.read()).decode("utf-8")

        context = {
            "run_id": run_id,
            "run": run,
            "health": health,
            "metrics": metrics,
            "charts": charts,
            "chart_images": chart_images,
            "alerts": alerts,
            "narrative": narrative,
            "stat_tests": stat_tests,
            "vintage": vintage,
            "override": override,
            "fairness": fairness,
            "segments": segments,
            "insights": insights,
            "timeseries": timeseries,
            "sections": sections,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "kpmg_logo_b64": kpmg_logo_b64,
        }
        
        html_content = template.render(**context)
        
        report_id = f"report_{uuid.uuid4().hex[:8]}"
        out_path = run_store._run_dir(run_id) / f"{report_id}.{fmt.value}"
        
        if fmt == ReportFormat.HTML:
            out_path.write_text(html_content, encoding="utf-8")
        elif fmt == ReportFormat.PDF:
            import subprocess
            # Always save an intermediate HTML file to feed into Puppeteer
            temp_html_path = run_store._run_dir(run_id) / f"{report_id}_temp.html"
            temp_html_path.write_text(html_content, encoding="utf-8")
            
            script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "generate_pdf.js")
            try:
                env = os.environ.copy()
                env["NVM_DIR"] = os.path.expanduser("~/.nvm")
                cmd = f'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && \\. "$NVM_DIR/nvm.sh" && node {script_path} {temp_html_path} {out_path}'
                subprocess.run(cmd, shell=True, check=True, capture_output=True, env=env)
            except subprocess.CalledProcessError as e:
                logger.error(f"Puppeteer PDF generation failed: {e.stderr.decode()}")
                # Graceful fallback in case Puppeteer fails
                out_path = run_store._run_dir(run_id) / f"{report_id}.html"
                out_path.write_text(html_content, encoding="utf-8")
                fmt = ReportFormat.HTML
            finally:
                if temp_html_path.exists():
                    os.remove(temp_html_path)
                    
        elif fmt == ReportFormat.DOCX:
            from app.services.docx_builder import DocxReportBuilder
            builder = DocxReportBuilder()
            builder.build(context, out_path, report_type.value)
            
        # Optional: could save metadata about generated reports to a reports.json in the run dir
        reports_meta = run_store.load_artifact(run_id, "reports.json") or []
        reports_meta.append({
            "report_id": report_id,
            "report_type": report_type.value,
            "format": fmt.value,
            "file_path": str(out_path),
            "download_url": f"/api/v1/runs/{run_id}/reports/{report_id}/download",
            "size_bytes": out_path.stat().st_size,
            "generated_at": datetime.now(timezone.utc).isoformat()
        })
        run_store.save_artifact(run_id, "reports.json", reports_meta)
        
        return out_path
