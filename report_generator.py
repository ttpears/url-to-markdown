import json
from pathlib import Path
from datetime import datetime
import os

def generate_report(results, base_path, video_file_path):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Crawl Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ max-width: 1400px; margin: auto; padding: 20px; }}
            h1, h2, p {{ color: #333; }}
            .summary {{ padding: 10px; background: #f9f9f9; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; cursor: pointer; }}
            th.sortable:hover {{ background-color: #eee; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Crawl Report - {timestamp}</h1>
            <div class="summary">
                <h2>Summary</h2>
                <p>Total pages crawled: {total_pages}</p>
                <p>Video: <a href="{video_link}">Download</a></p>
            </div>
            <h2>Detailed Report</h2>
            <table id="reportTable">
                <thead>
                <tr>
                    <th class="sortable" onclick="sortTable(0)">URL</th>
                    <th class="sortable" onclick="sortTable(1)">Status</th>
                    <th class="sortable" onclick="sortTable(2)">Response Code</th>
                    <th class="sortable" onclick="sortTable(3)">Content Length (KB)</th>
                    <th class="sortable" onclick="sortTable(4)">Assets</th>
                    <th class="sortable" onclick="sortTable(5)">Load Time (s)</th>
                    <th class="sortable" onclick="sortTable(6)">TTFB (s)</th>
                    <th>Screenshot</th>
                </tr>
                </thead>
                <tbody>
                {non_successful}
                {successful}
                </tbody>
            </table>
        </div>
        <script>
            function sortTable(n) {{
                var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
                table = document.getElementById("reportTable");
                switching = true;
                dir = "asc";
                while (switching) {{
                    switching = false;
                    rows = table.rows;
                    for (i = 1; i < (rows.length - 1); i++) {{
                        shouldSwitch = false;
                        x = rows[i].getElementsByTagName("TD")[n];
                        y = rows[i + 1].getElementsByTagName("TD")[n];
                        if (dir == "asc") {{
                            if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {{
                                shouldSwitch = true;
                                break;
                            }}
                        }} else if (dir == "desc") {{
                            if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) {{
                                shouldSwitch = true;
                                break;
                            }}
                        }}
                    }}
                    if (shouldSwitch) {{
                        rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                        switching = true;
                        switchcount ++;
                    }} else {{
                        if (switchcount == 0 && dir == "asc") {{
                            dir = "desc";
                            switching = true;
                        }}
                    }}
                }}
            }}
        </script>
    </body>
    </html>
    """

    non_successful_html = ""
    successful_html = ""
    json_report = {
        "timestamp": timestamp,
        "total_pages_crawled": len(results),
        "video": video_file_path if video_file_path else "N/A",
        "details": []
    }

    print("Generating HTML report...")
    for result in results:
        screenshot_path = result.get('screenshot', "N/A")
        relative_screenshot_path = (
            os.path.relpath(screenshot_path, os.path.join(base_path, "reports"))
            if screenshot_path != "N/A" and Path(screenshot_path).exists()
            else "N/A"
        )

        content_length = "{:.2f}".format(result['content_length']) if isinstance(result['content_length'], (int, float)) else "N/A"
        load_time = "{:.2f}".format(result['load_time']) if isinstance(result['load_time'], (int, float)) else "N/A"
        ttfb = "{:.2f}".format(result['ttfb']) if isinstance(result['ttfb'], (int, float)) else "N/A"

        row_template = """
            <tr>
                <td>{url}</td>
                <td>{status}</td>
                <td>{response_code}</td>
                <td>{content_length} KB</td>
                <td>{assets_count}</td>
                <td>{load_time}</td>
                <td>{ttfb}</td>
                <td><a href="{screenshot}" target="_blank">Screenshot</a></td>
            </tr>
        """

        row = row_template.format(
            url=result['url'],
            status=result.get('status', 'error'),
            response_code=result['response_code'],
            content_length=content_length,
            assets_count=result['assets_count'],
            load_time=load_time,
            ttfb=ttfb,
            screenshot=relative_screenshot_path
        )

        if 'error' in result or result['status'] != 'success':
            non_successful_html += row
        else:
            successful_html += row

        json_report["details"].append(result)

    relative_video_link = (
        os.path.relpath(video_file_path, os.path.join(base_path, "reports"))
        if video_file_path and Path(video_file_path).exists()
        else "N/A"
    )

    html_report = html_template.format(
        timestamp=timestamp,
        total_pages=len(results),
        video_link=relative_video_link,
        non_successful=non_successful_html,
        successful=successful_html
    )

    reports_path = Path(base_path) / "reports"
    reports_path.mkdir(parents=True, exist_ok=True)

    print(f"Writing HTML report to {reports_path / 'report.html'}")
    with open(reports_path / "report.html", "w") as f:
        f.write(html_report)

    print(f"Writing JSON report to {reports_path / 'report.json'}")
    with open(reports_path / "report.json", "w") as f:
        json.dump(json_report, f, indent=4)

    print(f"\nReports saved to {reports_path.resolve()}")

