"""
Output Formatter - Unified service for all output formatting.
Consolidates: enricher + html + csv + aggregate into one reusable service.
Uses branching logic: org vs repo detection.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class OutputFormatter:
    """
    Unified output formatter with branching logic.
    Handles enrichment, HTML, CSV, and aggregation in one service.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get base directory from user config
        self.base_dir = self._get_base_dir()
    
    def _get_base_dir(self) -> Path:
        """Get base directory from user config, fallback to current directory"""
        from core.initialization import get_user_config_file
        import yaml
        
        try:
            user_config_file = get_user_config_file()
            if user_config_file.exists():
                with open(user_config_file, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)
                    if user_config and 'base_directory' in user_config:
                        base_dir = Path(user_config['base_directory'])
                        return base_dir
        except Exception:
            pass
        
        # Fallback to current directory
        return Path('.')
    
    async def format_and_save(
        self,
        analysis_result: Dict[str, Any],
        is_organization: bool = False
    ) -> Dict[str, Any]:
        """
        Main formatting method with branching logic.
        Returns information about saved files.
        """
        try:
            if is_organization:
                return await self._format_organization(analysis_result)
            else:
                return await self._format_single_repo(analysis_result)
                
        except Exception as e:
            logger.error(f"Output formatting failed: {e}", exc_info=True)
            raise
    
    async def _format_single_repo(
        self, 
        analysis_result: Dict[str, Any], 
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Format single repository results.
        Enrichment → HTML → CSV → Save
        Only difference: save folder (parameter)
        """
        repo_name = analysis_result['repository']
        findings = analysis_result['findings']
        
        # Enrichment step
        enriched_data = self._enrich_findings(findings, repo_name)
        
        # Create output directory (different for single repo vs org)
        if output_dir is None:
            # Standalone single repo
            output_dir = self.base_dir / "reports" / f"{repo_name}_{self.timestamp}"
        else:
            # Repo within organization
            output_dir = output_dir / repo_name
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        files_saved = []
        
        # Save enriched JSON
        json_file = output_dir / f"{repo_name}_analysis.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, indent=2, ensure_ascii=False)
        files_saved.append(str(json_file))
        
        # Generate and save HTML
        html_content = self._generate_html_report(enriched_data, repo_name, output_dir)
        html_file = output_dir / f"{repo_name}_analysis.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        files_saved.append(str(html_file))
        
        # Generate and save CSV
        csv_content = self._generate_csv_report(enriched_data)
        csv_file = output_dir / f"{repo_name}_analysis.csv"
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            f.write(csv_content)
        files_saved.append(str(csv_file))
        
        # Extract target_jdk from findings (assuming all findings have same target_jdk)
        target_jdk = '21'  # default fallback
        if findings and len(findings) > 0:
            target_jdk = findings[0].get('target_jdk', '21')
        
        # Create summary for aggregation (used by org)
        summary = {
            'repository': repo_name,
            'total_issues': len(findings),
            'critical_issues': len([f for f in findings if f.get('severity') == 'error']),
            'warning_issues': len([f for f in findings if f.get('severity') == 'warning']),
            'info_issues': len([f for f in findings if f.get('severity') == 'info']),
            'target_jdk': target_jdk,
            'migration_readiness': enriched_data.get('migration_readiness', 'UNKNOWN'),
            'migration_reason': enriched_data.get('migration_reason', 'Status not calculated'),
            'files_saved': files_saved
        }
        
        return {
            'type': 'single_repo',
            'output_directory': str(output_dir),
            'files_saved': files_saved,
            'total_files': len(files_saved),
            'summary': summary
        }
    
    async def _format_organization(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format organization results.
        Process each repo → Aggregate → Create org structure
        """
        org_name = analysis_result['organization']
        repositories = analysis_result['repositories']
        
        # Extract just the directory name for local paths (fix for local org analysis)
        if '\\' in org_name or '/' in org_name:
            # Local org analysis - extract just the directory name
            org_display_name = Path(org_name).name
        else:
            # Remote org analysis - use as-is
            org_display_name = org_name
        
        # Create organization output directory
        org_output_dir = self.base_dir / "reports" / f"{org_display_name}_{self.timestamp}"
        org_output_dir.mkdir(parents=True, exist_ok=True)
        
        files_saved = []
        
        # Process each repository (reuse single repo logic)
        repo_summaries = []
        for repo_data in repositories:
            repo_result = await self._format_single_repo(repo_data, org_output_dir)
            files_saved.extend(repo_result['files_saved'])
            repo_summaries.append(repo_result['summary'])
        
        # Create organization aggregate report
        aggregate_data = self._create_aggregate_report(org_display_name, repo_summaries, analysis_result)
        
        # Save organization JSON
        org_json_file = org_output_dir / f"{org_display_name}_organization_summary.json"
        with open(org_json_file, 'w', encoding='utf-8') as f:
            json.dump(aggregate_data, f, indent=2, ensure_ascii=False)
        files_saved.append(str(org_json_file))
        
        # Save organization HTML
        org_html_content = self._generate_organization_html(aggregate_data, org_display_name)
        org_html_file = org_output_dir / f"{org_display_name}_organization_summary.html"
        with open(org_html_file, 'w', encoding='utf-8') as f:
            f.write(org_html_content)
        files_saved.append(str(org_html_file))
        
        # Save organization CSV
        org_csv_content = self._generate_organization_csv(aggregate_data)
        org_csv_file = org_output_dir / f"{org_display_name}_organization_summary.csv"
        with open(org_csv_file, 'w', encoding='utf-8', newline='') as f:
            f.write(org_csv_content)
        files_saved.append(str(org_csv_file))
        
        return {
            'type': 'organization',
            'output_directory': str(org_output_dir),
            'files_saved': files_saved,
            'total_files': len(files_saved),
            'repositories_processed': len(repositories)
        }

    def _enrich_findings(self, findings: List[Dict[str, Any]], repo_name: str) -> Dict[str, Any]:
        """
        Enrich raw findings with metadata and summary.
        Consolidates enricher service logic.
        """
        # Normalize findings - map JAR field names to template field names
        normalized_findings = []
        for finding in findings:
            # Extract method/constructor name from various JAR fields
            method_name = finding.get('method_name')
            if not method_name:
                # Try constructor field
                method_name = finding.get('constructor')
            if not method_name:
                # Extract from signature (e.g., "class java.security.acl.NotOwnerException" → "NotOwnerException")
                signature = finding.get('signature', '')
                if signature.startswith('class '):
                    # Class signature: extract class name
                    method_name = signature.replace('class ', '').split('.')[-1]
                elif '(' in signature:
                    # Method signature: extract method name
                    method_name = signature.split('(')[0].split('.')[-1].split(' ')[-1]
                else:
                    method_name = 'Unknown Method'
            
            normalized = {
                # Map JAR fields to template fields
                'type': method_name,
                'file': finding.get('file', 'Unknown'),
                'line': finding.get('line_number', 'Unknown'),
                'description': finding.get('reason', 'No description'),
                'severity': finding.get('severity', 'info'),
                'category': finding.get('reason', 'Unknown'),
                # Keep original fields for JSON output
                **finding
            }
            normalized_findings.append(normalized)
        
        # Calculate summary statistics
        total_issues = len(normalized_findings)
        severity_counts = {
            'critical': len([f for f in normalized_findings if f.get('severity') == 'error']),
            'warning': len([f for f in normalized_findings if f.get('severity') == 'warning']),
            'info': len([f for f in normalized_findings if f.get('severity') == 'info'])
        }
        
        # Calculate migration readiness status
        if severity_counts['critical'] > 0:
            migration_status = 'BLOCKED'
            migration_reason = f"{severity_counts['critical']} critical issues require immediate attention"
        elif severity_counts['warning'] > 0:
            migration_status = 'READY WITH TECH DEBT'
            migration_reason = f"{severity_counts['warning']} warnings should be reviewed"
        else:
            migration_status = 'READY'
            migration_reason = 'No blocking issues found'
        
        # Group by category/type
        categories = {}
        for finding in normalized_findings:
            category = finding.get('category', 'Unknown')
            if category not in categories:
                categories[category] = []
            categories[category].append(finding)
        
        return {
            'repository': repo_name,
            'analysis_timestamp': datetime.now().isoformat(),
            'migration_readiness': migration_status,
            'migration_reason': migration_reason,
            'summary': {
                'total_issues': total_issues,
                'severity_breakdown': severity_counts,
                'categories': {cat: len(items) for cat, items in categories.items()}
            },
            'findings': normalized_findings,
            'categories': categories
        }
    
    def _generate_html_report(self, enriched_data: Dict[str, Any], repo_name: str, output_dir: Path) -> str:
        """
        Generate HTML report using template file.
        Consolidates HTML conversion service logic.
        """
        import os
        from pathlib import Path
        
        # Load HTML template from working directory only
        template_path = self.base_dir / 'templates' / 'single_repo_report.html'
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found in working directory: {template_path}")
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Could not read template: {template_path}")
        
        # Determine logo path based on output directory depth
        # Single repo: reports/repo_name_timestamp/ -> ../../resources/graphshift-logo.png
        # Org repo: reports/org_name_timestamp/repo_name/ -> ../../../resources/graphshift-logo.png
        output_parts = output_dir.parts
        if len(output_parts) >= 5 and 'reports' in output_parts:
            # Org structure: reports/org_name_timestamp/repo_name/ (5+ parts)
            logo_path = "../../../resources/graphshift-logo.png"
        else:
            # Single repo structure: reports/repo_name_timestamp/ (4 parts)
            logo_path = "../../resources/graphshift-logo.png"
        
        findings = enriched_data['findings']
        summary = enriched_data['summary']
        
        # Generate table rows
        table_rows = []
        for finding in findings:
            severity = finding.get('severity', 'info')
            method_name = finding.get('type', finding.get('method_name', 'Unknown Method'))
            signature = finding.get('signature', '')
            deprecated_since = finding.get('deprecated_since', 'Unknown')
            removed_in = finding.get('removed_in', 'N/A')
            years_deprecated = finding.get('years_deprecated', 'Unknown')
            file_path = finding.get('file', 'Unknown')
            line_num = finding.get('line', 'Unknown')
            
            # Embed line number in file path
            file_with_line = f"{file_path} ({line_num})" if line_num != 'Unknown' else file_path
            
            # Create severity dot instead of badge
            severity_dot = f'<span class="severity-dot {severity}"></span>'
            
            row = f'''
                <tr class="finding-row" data-severity="{severity}" data-jdk="{deprecated_since}">
                    <td><span class="method-name">{method_name}</span></td>
                    <td><span class="file-path">{file_with_line}</span></td>
                    <td>{severity_dot}</td>
                    <td class="signature-cell"><code>{signature}</code></td>
                </tr>'''
            table_rows.append(row)
        
        # Extract target JDK from findings (all findings should have same target)
        target_jdk = "21"  # default
        if findings and len(findings) > 0:
            target_jdk = findings[0].get('target_jdk', '21')
        
        # Determine scope based on severity distribution
        scope = "All Deprecations"  # default
        severity_breakdown = summary.get('severity_breakdown', {})
        if severity_breakdown.get('warning', 0) == 0 and severity_breakdown.get('info', 0) == 0:
            scope = "Upgrade Blockers"
        
        # Format timestamp for human readability
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(enriched_data['analysis_timestamp'].replace('Z', '+00:00'))
            formatted_timestamp = dt.strftime("%B %d, %Y at %I:%M %p")
        except:
            formatted_timestamp = enriched_data['analysis_timestamp']
        
        
        # Fill template placeholders
        try:
            html_content = template.format(
                repo_name=repo_name,
                analysis_timestamp=formatted_timestamp,
                target_jdk=target_jdk,
                scope=scope,
                logo_path=logo_path,
                total_issues=summary['total_issues'],
                critical_count=summary['severity_breakdown']['critical'],
                warning_count=summary['severity_breakdown']['warning'],
                info_count=summary['severity_breakdown']['info'],
                table_rows=''.join(table_rows)
            )
            return html_content
        except Exception as e:
            logger.error(f"Template formatting failed: {e}")
            return self._generate_simple_html_fallback(enriched_data, repo_name)
    
    def _generate_simple_html_fallback(self, enriched_data: Dict[str, Any], repo_name: str) -> str:
        """Simple HTML fallback if template file not found"""
        findings = enriched_data['findings']
        summary = enriched_data['summary']
        
        rows = []
        for finding in findings:
            method_name = finding.get('type', 'Unknown')
            file_path = finding.get('file', 'Unknown')
            line_num = finding.get('line', 'Unknown')
            severity = finding.get('severity', 'info')
            
            rows.append(f"<tr><td>{method_name}</td><td>{file_path}</td><td>{line_num}</td><td>{severity}</td></tr>")
        
        return f"""
<!DOCTYPE html>
<html>
<head><title>GraphShift Analysis - {repo_name}</title></head>
<body>
<h1>GraphShift Analysis - {repo_name}</h1>
<p>Total Issues: {summary['total_issues']}</p>
<table border="1">
<tr><th>Method</th><th>File</th><th>Line</th><th>Severity</th></tr>
{''.join(rows)}
</table>
</body>
</html>"""
    
    def _generate_csv_report(self, enriched_data: Dict[str, Any]) -> str:
        """
        Generate CSV report.
        Consolidates CSV conversion service logic.
        """
        findings = enriched_data['findings']
        
        # CSV header
        csv_lines = ["Repository,File,Line,Type,Severity,Description,Category"]
        
        # CSV data
        repo_name = enriched_data['repository']
        for finding in findings:
            line = f'"{repo_name}","{finding.get("file", "")}","{finding.get("line", "")}","{finding.get("type", "")}","{finding.get("severity", "")}","{finding.get("description", "")}","{finding.get("category", "")}"'
            csv_lines.append(line)
        
        return "\n".join(csv_lines)
    
    def _create_aggregate_report(
        self, 
        org_name: str, 
        repo_summaries: List[Dict[str, Any]], 
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create organization aggregate report.
        Consolidates aggregate service logic.
        """
        total_issues = sum(repo['total_issues'] for repo in repo_summaries)
        total_critical = sum(repo['critical_issues'] for repo in repo_summaries)
        total_warning = sum(repo['warning_issues'] for repo in repo_summaries)
        total_info = sum(repo['info_issues'] for repo in repo_summaries)
        
        # Extract target_jdk from analysis_result or first repo
        target_jdk = analysis_result.get('target_jdk', '21')  # fallback to 21
        if not target_jdk or target_jdk == '21':
            # Try to get from first repo's data if available
            if repo_summaries and len(repo_summaries) > 0:
                first_repo_data = repo_summaries[0]
                target_jdk = first_repo_data.get('target_jdk', '21')
        
        return {
            'organization': org_name,
            'analysis_timestamp': datetime.now().isoformat(),
            'target_jdk': target_jdk,
            'summary': {
                'total_repositories': len(repo_summaries),
                'total_issues': total_issues,
                'severity_breakdown': {
                    'critical': total_critical,
                    'warning': total_warning,
                    'info': total_info
                }
            },
            'repositories': repo_summaries
        }
    
    def _generate_organization_html(self, aggregate_data: Dict[str, Any], org_name: str) -> str:
        """Generate organization-level HTML report using template"""
        try:
            # Load the organization template from working directory only
            template_path = self.base_dir / "templates" / "organization_report.html"
            
            if not template_path.exists():
                raise FileNotFoundError(f"Template not found in working directory: {template_path}")
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Could not read organization template: {template_path}")
        
        # Calculate logo path for organization report (always at org level: reports/org_timestamp/)
        logo_path = "../../resources/graphshift-logo.png"
        
        try:
            summary = aggregate_data['summary']
            repositories = aggregate_data['repositories']
            
            # Extract target JDK and scope from first repo (assuming all same)
            target_jdk = "21"  # default
            scope = "All Deprecations"  # default
            if repositories and len(repositories) > 0:
                # Try to get from first repo data
                first_repo = repositories[0]
                # Look for target_jdk in the aggregate data structure
                if 'target_jdk' in aggregate_data:
                    target_jdk = str(aggregate_data['target_jdk'])
                # Determine scope - if all critical, it's upgrade blockers
                if summary.get('severity_breakdown', {}).get('warning', 0) == 0 and summary.get('severity_breakdown', {}).get('info', 0) == 0:
                    scope = "Upgrade Blockers"
            
            # Format timestamp for human readability
            from datetime import datetime
            try:
                timestamp = aggregate_data['analysis_timestamp']
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_timestamp = dt.strftime("%B %d, %Y at %I:%M %p")
            except:
                formatted_timestamp = aggregate_data['analysis_timestamp']
            
            # Get totals from summary
            total_issues = summary['total_issues']
            total_critical = summary['severity_breakdown']['critical']
            total_warning = summary['severity_breakdown']['warning']
            total_info = summary['severity_breakdown']['info']
            
            # Generate repository rows with modern styling
            repo_rows = []
            for repo in repositories:
                repo_name = repo['repository']
                repo_total = repo['total_issues']
                repo_critical = repo['critical_issues']
                repo_warning = repo['warning_issues']
                repo_info = repo['info_issues']
                repo_files = repo.get('files_analyzed', 0)
                
                # Use pre-calculated readiness status from enriched data
                migration_status = repo.get('migration_readiness', 'UNKNOWN')
                if migration_status == 'BLOCKED':
                    status = '<span class="status-badge status-blocked">BLOCKED</span>'
                elif migration_status == 'READY WITH TECH DEBT':
                    status = '<span class="status-badge status-review">READY WITH TECH DEBT</span>'
                elif migration_status == 'READY':
                    status = '<span class="status-badge status-ready">READY</span>'
                else:
                    status = '<span class="status-badge status-unknown">UNKNOWN</span>'
                
                # Create link to individual repo report (opens in new window)
                repo_link = f'<a href="{repo_name}/{repo_name}_analysis.html" class="repo-link" target="_blank">{repo_name}</a>'
                
                repo_rows.append(f"""
                <tr>
                    <td>{repo_link}</td>
                    <td>{status}</td>
                    <td>{repo_total:,}</td>
                    <td>{repo_critical:,}</td>
                    <td>{repo_warning:,}</td>
                    <td>{repo_info:,}</td>
                </tr>""")
            
            repo_table_rows = "".join(repo_rows)
            
            # Fill template with data
            html_content = template.format(
                org_name=org_name,
                target_jdk=target_jdk,
                scope=scope,
                analysis_timestamp=formatted_timestamp,
                logo_path=logo_path,
                total_issues=f"{total_issues:,}",
                total_critical=f"{total_critical:,}",
                total_warning=f"{total_warning:,}",
                total_info=f"{total_info:,}",
                repo_rows=repo_table_rows
            )
            
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to generate organization HTML: {e}")
            # Fallback to simple HTML
            return f"<html><body><h1>Organization Report - {org_name}</h1><p>Error generating report: {e}</p></body></html>"
    
    def _generate_organization_csv(self, aggregate_data: Dict[str, Any]) -> str:
        """Generate organization-level CSV report"""
        repositories = aggregate_data['repositories']
        
        # CSV header
        csv_lines = ["Repository,Total_Issues,Critical_Issues,Warning_Issues,Info_Issues"]
        
        # CSV data
        for repo in repositories:
            line = f'"{repo["repository"]}",{repo["total_issues"]},{repo["critical_issues"]},{repo["warning_issues"]},{repo["info_issues"]}'
            csv_lines.append(line)
        
        return "\n".join(csv_lines)
    
    def _generate_simple_organization_fallback(self, aggregate_data: Dict[str, Any], org_name: str) -> str:
        """Simple HTML fallback for organization report if template file not found"""
        summary = aggregate_data['summary']
        repositories = aggregate_data['repositories']
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>GraphShift Analysis - {org_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .critical {{ color: red; font-weight: bold; }}
                .warning {{ color: orange; font-weight: bold; }}
                .info {{ color: blue; }}
            </style>
        </head>
        <body>
            <h1>GraphShift Analysis - {org_name}</h1>
            <h2>Organization Summary</h2>
            <p>Total Issues: {summary['total_issues']}</p>
            <p>Critical Issues: {summary['critical_issues']}</p>
            <p>Warning Issues: {summary['warning_issues']}</p>
            <p>Info Issues: {summary['info_issues']}</p>
            
            <h2>Repository Details</h2>
            <table>
                <tr>
                    <th>Repository</th>
                    <th>Total Issues</th>
                    <th>Critical</th>
                    <th>Warning</th>
                    <th>Info</th>
                </tr>
        """
        
        for repo in repositories:
            html += f"""
                <tr>
                    <td>{repo['repository']}</td>
                    <td>{repo['total_issues']}</td>
                    <td class="critical">{repo['critical_issues']}</td>
                    <td class="warning">{repo['warning_issues']}</td>
                    <td class="info">{repo['info_issues']}</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        return html