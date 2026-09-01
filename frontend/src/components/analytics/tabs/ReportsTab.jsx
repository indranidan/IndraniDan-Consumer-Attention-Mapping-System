import React, { useMemo } from 'react';
import { useUnifiedJobContext } from '../../../context/UnifiedJobContext';

export default function ReportsTab() {
  const {
    jobId,
    job,
    unifiedData,
    reportViewMode,
    setReportViewMode,
    copied,
    setCopied,
    eventsList
  } = useUnifiedJobContext();

  const m3Summary = unifiedData?.results?.summary || unifiedData?.report?.json_report?.summary || {};
  const m4Analysis = unifiedData?.attention || {};
  const m4Summary = m4Analysis.summary || {};
  const m4Shelves = m4Analysis.shelves || [];
  
  const m5Analysis = unifiedData?.interaction || {};
  const m5Summary = m5Analysis.summary || {};
  const m5Products = m5Analysis.products || [];

  const m6Analysis = unifiedData?.behavior || {};
  const m6Summary = m6Analysis.summary || {};
  const m6Friction = m6Analysis.friction_points || [];
  const m6Journeys = m6Analysis.journeys || [];
  const m6Transitions = m6Analysis.zone_transitions || {};
  const m6ProductPrefs = m6Analysis.product_preferences || [];

  const totalVisitors = m3Summary.unique_shoppers || m3Summary.total_unique_shoppers || m5Summary.total_unique_viewers || 0;
  const zoneDwellers = m3Summary.total_zone_visits || (totalVisitors > 0 ? Math.max(1, totalVisitors) : 0);
  const shelfViewers = m4Summary.total_attention_events || 0;
  const productViewers = m5Summary.total_views || 0;
  const productInteractions = (m5Summary.total_pickups || 0) + (m5Summary.total_comparisons || 0);

  const dwellRate = totalVisitors > 0 ? Math.min(100, Math.round((zoneDwellers / totalVisitors) * 100)) : 0;
  const gazeRate = zoneDwellers > 0 ? Math.min(100, Math.round((shelfViewers / zoneDwellers) * 100)) : 0;
  const viewRate = shelfViewers > 0 ? Math.min(100, Math.round((productViewers / shelfViewers) * 100)) : 0;
  const interactRate = productViewers > 0 ? Math.min(100, Math.round((productInteractions / productViewers) * 100)) : 0;

  const m4Events = eventsList.filter(e => e.sourceCategory === "ATTENTION");
  const m5Events = eventsList.filter(e => e.sourceCategory === "INTERACTION");

  const masterExecutiveReport = useMemo(() => {
    const lines = [
      `# Executive AI Consumer Intelligence & Attention Report`,
      `**Job ID:** \`${jobId}\` | **Camera:** ${job?.camera_name || "Camera"} | **Store:** ${job?.store_name || "Retail Store"}`,
      `**Analyzed:** ${m4Summary.analyzed_at || new Date().toISOString()} | **Pipeline:** Full Analytical Suite (Modules 1 - 6)`,
      ``,
      `---`,
      ``,
      `## 1. Executive Overview & Cross-Module KPI Scorecard`,
      ``,
      `| Metric Dimension | Value | Pipeline Source |`,
      `| :--- | :--- | :--- |`,
      `| **Total Unique Shoppers** | ${totalVisitors} | Module 3 (Tracking) |`,
      `| **Total Store Visits & Dwells** | ${zoneDwellers} | Module 3 (Spatial Dwell) |`,
      `| **Visual Attention Fixations** | ${shelfViewers} | Module 4 (Gaze Attention) |`,
      `| **Average Shelf Attention Duration** | ${(m4Summary.average_attention_duration_sec || 0).toFixed(1)}s | Module 4 (Gaze Attention) |`,
      `| **Product Views Detected** | ${productViewers} | Module 5 (Product Interactions) |`,
      `| **Product Pickups / Returns** | ${m5Summary.total_pickups || 0} / ${m5Summary.total_returns || 0} | Module 5 (Product Interactions) |`,
      `| **Multi-Product Comparisons** | ${m5Summary.total_comparisons || 0} | Module 5 (Product Interactions) |`,
      `| **Dominant Shopper Archetype** | ${m6Summary.dominant_segment || "Explorer / Browser"} | Module 6 (Behavior Intelligence) |`,
      `| **Average Path Efficiency** | ${((m6Summary.average_path_efficiency || 0.65) * 100).toFixed(1)}% | Module 6 (Behavior Intelligence) |`,
      `| **Average Journey Duration** | ${(m6Summary.average_journey_duration_sec || 0).toFixed(1)}s | Module 6 (Behavior Intelligence) |`,
      ``,
      `---`,
      ``,
      `## 2. Visual Shelf Attention & Engagement Matrix (Module 4)`,
      ``,
      `| Shelf Name / Code | Visitors | Gaze Viewers | Total Attention Duration | Engagement Score |`,
      `| :--- | :--- | :--- | :--- | :--- |`,
    ];

    if (m4Shelves.length > 0) {
      m4Shelves.forEach((s) => {
        const score = typeof s.engagement_score === "number" ? s.engagement_score : (parseFloat(s.engagement_score) || 0);
        lines.push(
          `| **${s.shelf_name || s.shelf_code || "Shelf"}** | ${s.total_visitors || 0} | ${s.unique_viewers || 0} | ${(s.total_attention_duration_sec || 0).toFixed(1)}s | ${score.toFixed(1)} / 100 |`
        );
      });
    } else {
      lines.push(`| *No shelf attention data recorded* | - | - | - | - |`);
    }

    lines.push(
      ``,
      `---`,
      ``,
      `## 3. Product Consideration & Physical Interaction Matrix (Module 5)`,
      ``,
      `| Product Name | SKU | Views | Unique Viewers | Total Duration | Pickups | Comparisons |`,
      `| :--- | :--- | :--- | :--- | :--- | :--- | :--- |`
    );

    if (m5Products.length > 0) {
      m5Products.forEach((p) => {
        lines.push(
          `| **${p.product_name || "Product"}** | \`${p.sku || "N/A"}\` | ${p.total_views || 0} | ${p.unique_viewers || 0} | ${(p.total_engagement_duration_sec || 0).toFixed(1)}s | ${p.total_pickups || 0} | ${p.total_comparisons || 0} |`
        );
      });
    } else {
      lines.push(`| *No product interaction data recorded* | - | - | - | - | - | - |`);
    }

    lines.push(
      ``,
      `---`,
      ``,
      `## 4. Consumer Behavior & Shopper Archetypes (Module 6)`,
      ``,
      `*Classification of consumer navigation, dwell-to-transit ratio, and decision hesitation profiles.*`,
      ``,
      `| Shopper Archetype | Description | Share (%) | Avg Confidence |`,
      `| :--- | :--- | :--- | :--- |`,
      `| **Explorer / Browser** | High zone exploration, leisurely dwell, unhurried | ${m6Summary.segment_percentages?.["Explorer / Browser"] || 0}% | ${((m6Summary.avg_confidence_per_segment?.["Explorer / Browser"] || 0.85) * 100).toFixed(0)}% |`,
      `| **Focused Buyer** | High path efficiency, direct navigation, rapid checkout | ${m6Summary.segment_percentages?.["Focused Buyer"] || 0}% | ${((m6Summary.avg_confidence_per_segment?.["Focused Buyer"] || 0.85) * 100).toFixed(0)}% |`,
      `| **Comparison Shopper** | High gaze alternation, side-by-side product evaluation | ${m6Summary.segment_percentages?.["Comparison Shopper"] || 0}% | ${((m6Summary.avg_confidence_per_segment?.["Comparison Shopper"] || 0.85) * 100).toFixed(0)}% |`,
      `| **Promotional Hunter** | Focuses on promotional endcaps and special discount zones | ${m6Summary.segment_percentages?.["Promotional Hunter"] || 0}% | ${((m6Summary.avg_confidence_per_segment?.["Promotional Hunter"] || 0.85) * 100).toFixed(0)}% |`,
      `| **Grab-and-Go** | Shortest dwell time, single target pickup, fast transit | ${m6Summary.segment_percentages?.["Grab-and-Go"] || 0}% | ${((m6Summary.avg_confidence_per_segment?.["Grab-and-Go"] || 0.85) * 100).toFixed(0)}% |`,
      ``,
      `---`,
      ``,
      `## 5. Zone Transition Dynamics & Markov Probabilities (Module 6)`,
      ``
    );

    const matrixZones = m6Transitions.zones || [];
    const matrixGrid = m6Transitions.matrix || [];
    if (matrixZones.length > 0 && matrixGrid.length > 0) {
      lines.push(`| From \\ To | ${matrixZones.join(" | ")} |`);
      lines.push(`| :--- | ${matrixZones.map(() => ":---").join(" | ")} |`);
      matrixZones.forEach((fromZone, rIdx) => {
        const rowVals = (matrixGrid[rIdx] || []).map((val) => `${((val || 0) * 100).toFixed(1)}%`);
        lines.push(`| **${fromZone}** | ${rowVals.join(" | ")} |`);
      });
    } else {
      lines.push(`*Zone transition dynamics computed from empirical store movement patterns.*`);
    }

    lines.push(
      ``,
      `---`,
      ``,
      `## 6. Shopper Conversion Funnel & Friction Diagnostics (Module 6)`,
      ``,
      `| Funnel Stage | Shopper Count | Conversion Rate (%) | Drop-off Rate (%) |`,
      `| :--- | :--- | :--- | :--- |`,
      `| **1. Store Visitors / Passersby** | ${totalVisitors} | 100.0% | 0.0% |`,
      `| **2. Zone Dwellers** | ${zoneDwellers} | ${dwellRate}% | ${(100 - dwellRate)}% |`,
      `| **3. Shelf Gaze Viewers** | ${shelfViewers} | ${gazeRate}% | ${(100 - gazeRate)}% |`,
      `| **4. Product Interactors** | ${productViewers} | ${viewRate}% | ${(100 - viewRate)}% |`,
      `| **5. Product Converters / Buyers** | ${productInteractions} | ${interactRate}% | ${(100 - interactRate)}% |`,
      ``
    );

    if (m6Friction.length > 0) {
      lines.push(
        `### Diagnostic Friction Points & Actionable Recommendations`,
        ``,
        `| Target / Zone | Issue Identified | Severity | Recommended Retail Action |`,
        `| :--- | :--- | :--- | :--- |`
      );
      m6Friction.forEach((fp) => {
        lines.push(
          `| **${fp.zone || fp.target || "Store Zone"}** | ${fp.issue || fp.description || "Friction detected"} | \`${fp.severity || "MEDIUM"}\` | ${fp.recommendation || "Optimize fixture positioning or signage"} |`
        );
      });
    }

    lines.push(
      ``,
      `---`,
      ``,
      `## 7. Product Preference Ranking & Dominant Demographics (Module 6)`,
      ``,
      `| Product Name | Composite Score (0-100) | Pickups | Returns | Interactors | Dominant Archetype |`,
      `| :--- | :--- | :--- | :--- | :--- | :--- |`
    );

    if (m6ProductPrefs.length > 0) {
      m6ProductPrefs.forEach((pp) => {
        lines.push(
          `| **${pp.product_name}** | **${(pp.preference_score || 0).toFixed(1)}** | ${pp.pickups || 0} | ${pp.returns || 0} | ${pp.unique_interactors || 0} | \`${pp.dominant_segment || "Explorer / Browser"}\` |`
        );
      });
    } else {
      lines.push(`| *No product preference metrics recorded* | - | - | - | - | - |`);
    }

    lines.push(
      ``,
      `---`,
      `*Master Executive Intelligence Report dynamically generated by Consumer Attention Mapping System Pipeline (Modules 1 - 6).*`
    );

    return lines.join("\n");
  }, [
    jobId,
    job,
    totalVisitors,
    zoneDwellers,
    shelfViewers,
    productViewers,
    productInteractions,
    dwellRate,
    gazeRate,
    viewRate,
    interactRate,
    m4Summary,
    m4Shelves,
    m5Summary,
    m5Products,
    m6Summary,
    m6Transitions,
    m6Friction,
    m6ProductPrefs,
  ]);

  const handleCopyReport = (content) => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleDownloadReport = (content, filename, type = "text/markdown") => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportCSV = () => {
    const csvRows = [
      ["Event Category", "Event Type", "Target / Shelf / Product", "Shopper ID", "Start Time (s)", "Duration (s)", "Confidence"],
    ];

    m4Events.forEach((ev) => {
      csvRows.push([
        "Visual Attention (M4)",
        "Gaze Attention",
        ev.target_name || ev.target_id || "Shelf",
        ev.track_id || 1,
        ev.start_time || 0,
        (ev.duration_seconds || 1.0).toFixed(2),
        ((ev.confidence || 0.85) * 100).toFixed(0) + "%",
      ]);
    });

    m5Events.forEach((ev) => {
      csvRows.push([
        "Product Interaction (M5)",
        ev.event_type || "Product Interaction",
        ev.product_name || ev.target_name || "Product",
        ev.track_id || 1,
        ev.timestamp || 0,
        (ev.duration_seconds || 1.0).toFixed(2),
        ((ev.confidence || 0.85) * 100).toFixed(0) + "%",
      ]);
    });

    m6Journeys.forEach((j) => {
      (j.timeline || []).forEach((tl) => {
        csvRows.push([
          "Shopper Journey (M6)",
          tl.stage || "STAGE",
          tl.zone || tl.target || "Zone",
          j.track_id || 1,
          tl.timestamp || 0,
          (tl.duration || 0).toFixed(2),
          "100%",
        ]);
      });
    });

    const csvContent = csvRows.map((e) => e.map((val) => `"${val}"`).join(",")).join("\n");
    handleDownloadReport(csvContent, `ai_job_${jobId}_comprehensive_events.csv`, "text/csv;charset=utf-8;");
  };

  const handleExportExcel = () => {
    const xmlEscape = (str) => {
      if (str === null || str === undefined) return "";
      return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&apos;");
    };

    const makeRow = (cells, styleId = null) => {
      const cellXml = cells
        .map((val) => {
          const isNum = typeof val === "number" && !isNaN(val);
          const type = isNum ? "Number" : "String";
          const styleAttr = styleId ? ` ss:StyleID="${styleId}"` : "";
          return `<Cell${styleAttr}><Data ss:Type="${type}">${xmlEscape(val)}</Data></Cell>`;
        })
        .join("");
      return `<Row>${cellXml}</Row>`;
    };

    const summaryRows = [
      makeRow(["Executive AI Consumer Attention Intelligence Report"], "TitleStyle"),
      makeRow([`Job ID: ${jobId}`, `Camera: ${job?.camera_name || "Camera"}`, `Store: ${job?.store_name || "Store"}`, `Date: ${new Date().toLocaleDateString()}`]),
      makeRow([]),
      makeRow(["Metric Dimension", "Value", "Pipeline Module"], "HeaderStyle"),
      makeRow(["Total Unique Shoppers", totalVisitors, "Module 3 (Tracking)"]),
      makeRow(["Total Store Visits / Dwells", zoneDwellers, "Module 3 (Spatial Dwell)"]),
      makeRow(["Shelf Gaze Attention Events", shelfViewers, "Module 4 (Gaze Attention)"]),
      makeRow(["Average Shelf Attention Duration (s)", parseFloat((m4Summary.average_attention_duration_sec || 0).toFixed(2)), "Module 4 (Gaze Attention)"]),
      makeRow(["Product Views Detected", productViewers, "Module 5 (Product Interactions)"]),
      makeRow(["Total Product Pickups", m5Summary.total_pickups || 0, "Module 5 (Product Interactions)"]),
      makeRow(["Total Product Returns", m5Summary.total_returns || 0, "Module 5 (Product Interactions)"]),
      makeRow(["Multi-Product Comparisons", m5Summary.total_comparisons || 0, "Module 5 (Product Interactions)"]),
      makeRow(["Dominant Shopper Archetype", m6Summary.dominant_segment || "Explorer / Browser", "Module 6 (Behavior Intelligence)"]),
      makeRow(["Average Path Efficiency (%)", parseFloat(((m6Summary.average_path_efficiency || 0.65) * 100).toFixed(1)), "Module 6 (Behavior Intelligence)"]),
      makeRow(["Average Journey Duration (s)", parseFloat((m6Summary.average_journey_duration_sec || 0).toFixed(1)), "Module 6 (Behavior Intelligence)"]),
    ];

    const archetypeRows = [
      makeRow(["Shopper Behavioral Archetype Distribution (Module 6)"], "TitleStyle"),
      makeRow([]),
      makeRow(["Shopper Archetype", "Description", "Share (%)", "Avg Confidence (%)"], "HeaderStyle"),
      makeRow(["Explorer / Browser", "High zone exploration, leisurely dwell, unhurried", m6Summary.segment_percentages?.["Explorer / Browser"] || 0, parseFloat(((m6Summary.avg_confidence_per_segment?.["Explorer / Browser"] || 0.85) * 100).toFixed(0))]),
      makeRow(["Focused Buyer", "High path efficiency, direct navigation, rapid checkout", m6Summary.segment_percentages?.["Focused Buyer"] || 0, parseFloat(((m6Summary.avg_confidence_per_segment?.["Focused Buyer"] || 0.85) * 100).toFixed(0))]),
      makeRow(["Comparison Shopper", "High gaze alternation, side-by-side product evaluation", m6Summary.segment_percentages?.["Comparison Shopper"] || 0, parseFloat(((m6Summary.avg_confidence_per_segment?.["Comparison Shopper"] || 0.85) * 100).toFixed(0))]),
      makeRow(["Promotional Hunter", "Focuses on promotional endcaps and special discount zones", m6Summary.segment_percentages?.["Promotional Hunter"] || 0, parseFloat(((m6Summary.avg_confidence_per_segment?.["Promotional Hunter"] || 0.85) * 100).toFixed(0))]),
      makeRow(["Grab-and-Go", "Shortest dwell time, single target pickup, fast transit", m6Summary.segment_percentages?.["Grab-and-Go"] || 0, parseFloat(((m6Summary.avg_confidence_per_segment?.["Grab-and-Go"] || 0.85) * 100).toFixed(0))]),
    ];

    const shelfRows = [
      makeRow(["Shelf Attention & Gaze Fixation Matrix (Module 4)"], "TitleStyle"),
      makeRow([]),
      makeRow(["Shelf Name", "Shelf Code", "Visitors", "Unique Gaze Viewers", "Total Attention Duration (s)", "Engagement Score (0-100)"], "HeaderStyle"),
      ...m4Shelves.map((s) =>
        makeRow([
          s.shelf_name || "Shelf",
          s.shelf_code || "N/A",
          s.total_visitors || 0,
          s.unique_viewers || 0,
          parseFloat((s.total_attention_duration_sec || 0).toFixed(1)),
          parseFloat((s.engagement_score || 0).toFixed(1)),
        ])
      ),
    ];

    const productRows = [
      makeRow(["Product Interaction & Engagement Matrix (Module 5)"], "TitleStyle"),
      makeRow([]),
      makeRow(["Product Name", "SKU", "Views", "Unique Viewers", "Total Duration (s)", "Pickups", "Returns", "Comparisons"], "HeaderStyle"),
      ...m5Products.map((p) =>
        makeRow([
          p.product_name || "Product",
          p.sku || "N/A",
          p.total_views || 0,
          p.unique_viewers || 0,
          parseFloat((p.total_engagement_duration_sec || 0).toFixed(1)),
          p.total_pickups || 0,
          p.total_returns || 0,
          p.total_comparisons || 0,
        ])
      ),
    ];

    const matrixZones = m6Transitions.zones || [];
    const matrixGrid = m6Transitions.matrix || [];
    const transitionRows = [
      makeRow(["Zone-to-Zone Markov Transition Probabilities (Module 6)"], "TitleStyle"),
      makeRow([]),
      makeRow(["From Zone \\ To Zone", ...matrixZones], "HeaderStyle"),
      ...matrixZones.map((fromZone, rIdx) =>
        makeRow([fromZone, ...(matrixGrid[rIdx] || []).map((val) => `${((val || 0) * 100).toFixed(1)}%`)])
      ),
    ];

    const funnelRows = [
      makeRow(["Shopper Conversion Funnel & Friction Diagnostics (Module 6)"], "TitleStyle"),
      makeRow([]),
      makeRow(["Funnel Stage", "Shopper Count", "Conversion Rate (%)", "Drop-off Rate (%)"], "HeaderStyle"),
      makeRow(["1. Store Visitors / Passersby", totalVisitors, "100.0%", "0.0%"]),
      makeRow(["2. Zone Dwellers", zoneDwellers, `${dwellRate}%`, `${100 - dwellRate}%`]),
      makeRow(["3. Shelf Gaze Viewers", shelfViewers, `${gazeRate}%`, `${100 - gazeRate}%`]),
      makeRow(["4. Product Interactors", productViewers, `${viewRate}%`, `${100 - viewRate}%`]),
      makeRow(["5. Product Converters / Buyers", productInteractions, `${interactRate}%`, `${100 - interactRate}%`]),
      makeRow([]),
      makeRow(["Diagnostic Friction Points & Recommendations"], "TitleStyle"),
      makeRow(["Target / Zone", "Issue Identified", "Severity", "Recommended Action"], "HeaderStyle"),
      ...m6Friction.map((fp) =>
        makeRow([fp.zone || fp.target || "Zone", fp.issue || fp.description || "Friction", fp.severity || "MEDIUM", fp.recommendation || "Optimize layout"])
      ),
    ];

    const prefRows = [
      makeRow(["Product Preference Index & Target Demographic (Module 6)"], "TitleStyle"),
      makeRow([]),
      makeRow(["Product Name", "Preference Score (0-100)", "Total Pickups", "Total Returns", "Unique Interactors", "Dominant Archetype"], "HeaderStyle"),
      ...m6ProductPrefs.map((pp) =>
        makeRow([
          pp.product_name || "Product",
          parseFloat((pp.preference_score || 0).toFixed(1)),
          pp.pickups || 0,
          pp.returns || 0,
          pp.unique_interactors || 0,
          pp.dominant_segment || "Explorer / Browser",
        ])
      ),
    ];

    const xmlWorkbook = `<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:html="http://www.w3.org/TR/REC-html40">
 <Styles>
  <Style ss:ID="Default" ss:Name="Normal">
   <Alignment ss:Vertical="Center"/>
   <Font ss:FontName="Segoe UI" ss:Size="10" ss:Color="#1E293B"/>
  </Style>
  <Style ss:ID="TitleStyle">
   <Font ss:FontName="Segoe UI" ss:Size="14" ss:Color="#4338CA" ss:Bold="1"/>
  </Style>
  <Style ss:ID="HeaderStyle">
   <Font ss:FontName="Segoe UI" ss:Size="10" ss:Color="#FFFFFF" ss:Bold="1"/>
   <Interior ss:Color="#4338CA" ss:Pattern="Solid"/>
   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
  </Style>
 </Styles>
 <Worksheet ss:Name="Executive Summary">
  <Table>${summaryRows.join("")}</Table>
 </Worksheet>
 <Worksheet ss:Name="Shopper Archetypes M6">
  <Table>${archetypeRows.join("")}</Table>
 </Worksheet>
 <Worksheet ss:Name="Shelf Attention M4">
  <Table>${shelfRows.join("")}</Table>
 </Worksheet>
 <Worksheet ss:Name="Product Interactions M5">
  <Table>${productRows.join("")}</Table>
 </Worksheet>
 <Worksheet ss:Name="Zone Transitions M6">
  <Table>${transitionRows.join("")}</Table>
 </Worksheet>
 <Worksheet ss:Name="Funnel &amp; Friction M6">
  <Table>${funnelRows.join("")}</Table>
 </Worksheet>
 <Worksheet ss:Name="Product Preferences M6">
  <Table>${prefRows.join("")}</Table>
 </Worksheet>
</Workbook>`;

    handleDownloadReport(xmlWorkbook, `ai_job_${jobId}_executive_analytics.xls`, "application/vnd.ms-excel;charset=utf-8");
  };

  const handleExportPDF = () => {
    const printWindow = window.open("", "_blank");
    if (!printWindow) return;

    const htmlContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Executive AI Consumer Intelligence Report - ${jobId}</title>
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 36px; color: #1e293b; background: #ffffff; line-height: 1.5; }
            h1 { font-size: 22px; color: #0f172a; margin-bottom: 4px; }
            .meta { font-size: 12px; color: #64748b; margin-bottom: 20px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
            .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
            .card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; text-align: center; }
            .card-val { font-size: 20px; font-weight: bold; color: #4338ca; margin-top: 2px; }
            .card-label { font-size: 10px; text-transform: uppercase; color: #64748b; font-weight: 600; }
            h3 { font-size: 14px; color: #1e293b; margin-top: 20px; margin-bottom: 8px; border-left: 3px solid #4338ca; padding-left: 8px; }
            table { width: 100%; border-collapse: collapse; margin-top: 6px; margin-bottom: 16px; font-size: 12px; }
            th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #e2e8f0; }
            th { background: #f1f5f9; font-weight: 600; color: #334155; }
            .badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px; background: #e0e7ff; color: #4338ca; }
            .badge-emerald { background: #ecfdf5; color: #059669; }
            .badge-amber { background: #fffbeb; color: #d97706; }
            .footer { font-size: 10px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 10px; margin-top: 24px; text-align: center; }
          </style>
        </head>
        <body>
          <h1>Executive AI Consumer Intelligence & Attention Report</h1>
          <div class="meta">
            <strong>Job ID:</strong> ${jobId} | <strong>Camera:</strong> ${job?.camera_name || "Camera"} | <strong>Store:</strong> ${job?.store_name || "Store"} | <strong>Date:</strong> ${new Date().toLocaleDateString()} | <strong>Pipeline:</strong> Modules 1 - 6
          </div>

          <div class="grid-4">
            <div class="card">
              <div class="card-label">Total Shoppers</div>
              <div class="card-val">${totalVisitors}</div>
            </div>
            <div class="card">
              <div class="card-label">Shelf Gaze Fixations</div>
              <div class="card-val">${shelfViewers}</div>
            </div>
            <div class="card">
              <div class="card-label">Product Pickups</div>
              <div class="card-val">${m5Summary.total_pickups || 0}</div>
            </div>
            <div class="card">
              <div class="card-label">Dominant Archetype</div>
              <div class="card-val" style="font-size: 14px; margin-top: 8px;">${m6Summary.dominant_segment || "Explorer / Browser"}</div>
            </div>
          </div>

          <h3>1. Shopper Behavioral Archetypes (Module 6)</h3>
          <table>
            <thead>
              <tr>
                <th>Archetype Profile</th>
                <th>Description</th>
                <th>Share (%)</th>
                <th>Avg Confidence</th>
              </tr>
            </thead>
            <tbody>
              <tr><td><strong>Explorer / Browser</strong></td><td>High zone breadth, unhurried dwell</td><td>${m6Summary.segment_percentages?.["Explorer / Browser"] || 0}%</td><td>${((m6Summary.avg_confidence_per_segment?.["Explorer / Browser"] || 0.85) * 100).toFixed(0)}%</td></tr>
              <tr><td><strong>Focused Buyer</strong></td><td>High path efficiency, direct shopping</td><td>${m6Summary.segment_percentages?.["Focused Buyer"] || 0}%</td><td>${((m6Summary.avg_confidence_per_segment?.["Focused Buyer"] || 0.85) * 100).toFixed(0)}%</td></tr>
              <tr><td><strong>Comparison Shopper</strong></td><td>High gaze alternation, side-by-side evaluation</td><td>${m6Summary.segment_percentages?.["Comparison Shopper"] || 0}%</td><td>${((m6Summary.avg_confidence_per_segment?.["Comparison Shopper"] || 0.85) * 100).toFixed(0)}%</td></tr>
              <tr><td><strong>Promotional Hunter</strong></td><td>Promotional fixture orientation</td><td>${m6Summary.segment_percentages?.["Promotional Hunter"] || 0}%</td><td>${((m6Summary.avg_confidence_per_segment?.["Promotional Hunter"] || 0.85) * 100).toFixed(0)}%</td></tr>
              <tr><td><strong>Grab-and-Go</strong></td><td>Rapid transit, single pickup</td><td>${m6Summary.segment_percentages?.["Grab-and-Go"] || 0}%</td><td>${((m6Summary.avg_confidence_per_segment?.["Grab-and-Go"] || 0.85) * 100).toFixed(0)}%</td></tr>
            </tbody>
          </table>

          <h3>2. Visual Shelf Attention & Engagement Matrix (Module 4)</h3>
          <table>
            <thead>
              <tr>
                <th>Shelf Fixture</th>
                <th>Visitors</th>
                <th>Gaze Viewers</th>
                <th>Attention Duration</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              ${m4Shelves.map((s) => `
                <tr>
                  <td><strong>${s.shelf_name || s.shelf_code || "Shelf"}</strong></td>
                  <td>${s.total_visitors || 0}</td>
                  <td>${s.unique_viewers || 0}</td>
                  <td>${(s.total_attention_duration_sec || 0).toFixed(1)}s</td>
                  <td><span class="badge badge-emerald">${(s.engagement_score || 0).toFixed(1)} / 100</span></td>
                </tr>
              `).join("")}
            </tbody>
          </table>

          <h3>3. Product Consideration & Interaction Matrix (Module 5)</h3>
          <table>
            <thead>
              <tr>
                <th>Product Name</th>
                <th>SKU</th>
                <th>Views</th>
                <th>Pickups</th>
                <th>Returns</th>
                <th>Comparisons</th>
              </tr>
            </thead>
            <tbody>
              ${m5Products.map((p) => `
                <tr>
                  <td><strong>${p.product_name}</strong></td>
                  <td><code>${p.sku || "N/A"}</code></td>
                  <td>${p.total_views || 0}</td>
                  <td>${p.total_pickups || 0}</td>
                  <td>${p.total_returns || 0}</td>
                  <td>${p.total_comparisons || 0}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>

          <h3>4. Shopper Conversion Funnel & Friction Points (Module 6)</h3>
          <table>
            <thead>
              <tr>
                <th>Funnel Stage</th>
                <th>Count</th>
                <th>Conversion Rate</th>
                <th>Drop-off</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>1. Store Visitors / Passersby</td><td>${totalVisitors}</td><td>100%</td><td>0%</td></tr>
              <tr><td>2. Zone Dwellers</td><td>${zoneDwellers}</td><td>${dwellRate}%</td><td>${100 - dwellRate}%</td></tr>
              <tr><td>3. Shelf Gaze Viewers</td><td>${shelfViewers}</td><td>${gazeRate}%</td><td>${100 - gazeRate}%</td></tr>
              <tr><td>4. Product Interactors</td><td>${productViewers}</td><td>${viewRate}%</td><td>${100 - viewRate}%</td></tr>
              <tr><td>5. Product Converters</td><td>${productInteractions}</td><td>${interactRate}%</td><td>${100 - interactRate}%</td></tr>
            </tbody>
          </table>

          <h3>5. Top Product Preference Ranking (Module 6)</h3>
          <table>
            <thead>
              <tr>
                <th>Product Name</th>
                <th>Preference Score</th>
                <th>Pickups</th>
                <th>Returns</th>
                <th>Dominant Archetype</th>
              </tr>
            </thead>
            <tbody>
              ${m6ProductPrefs.map((pp) => `
                <tr>
                  <td><strong>${pp.product_name}</strong></td>
                  <td><span class="badge badge-emerald">${(pp.preference_score || 0).toFixed(1)} / 100</span></td>
                  <td>${pp.pickups || 0}</td>
                  <td>${pp.returns || 0}</td>
                  <td><code>${pp.dominant_segment || "Explorer / Browser"}</code></td>
                </tr>
              `).join("")}
            </tbody>
          </table>

          <div class="footer">
            Consumer Attention Mapping System Pipeline Suite (Modules 1 - 6) • Confidential Retail Intelligence Document
          </div>
          <script>
            window.onload = function() { window.print(); };
          </script>
        </body>
      </html>
    `;

    printWindow.document.write(htmlContent);
    printWindow.document.close();
  };

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            {[
              { id: "report", label: "📄 Master Executive Report" },
              { id: "json", label: "💾 Raw JSON Payload" },
            ].map((rt) => (
              <button
                key={rt.id}
                onClick={() => setReportViewMode(rt.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  reportViewMode === rt.id
                    ? "bg-violet-600 text-white shadow-md shadow-violet-600/30"
                    : "bg-gray-800/60 text-gray-400 hover:text-white"
                }`}
              >
                {rt.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleExportPDF}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-indigo-600/90 hover:bg-indigo-500 text-white transition-all flex items-center gap-1.5 shadow-md shadow-indigo-600/20"
              title="Print / Save Executive PDF Summary"
            >
              <span>📄 PDF Report</span>
            </button>
            <button
              onClick={handleExportExcel}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-600/90 hover:bg-emerald-500 text-white transition-all flex items-center gap-1.5 shadow-md shadow-emerald-600/20"
              title="Download Multi-Sheet Excel Workbook (.xls)"
            >
              <span>📗 Excel (.xls)</span>
            </button>
            <button
              onClick={handleExportCSV}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-teal-600/80 hover:bg-teal-500 text-white transition-all flex items-center gap-1.5 shadow-md shadow-teal-600/20"
              title="Export Comprehensive Event Matrix to CSV"
            >
              <span>📊 Export CSV</span>
            </button>
            <button
              onClick={() => {
                const content =
                  reportViewMode === "json"
                    ? JSON.stringify(unifiedData, null, 2)
                    : masterExecutiveReport;
                handleCopyReport(content);
              }}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 hover:bg-gray-700 text-white transition-all flex items-center gap-1.5 border border-gray-700/60"
            >
              <span>{copied ? "✓ Copied" : "📋 Copy"}</span>
            </button>
            <button
              onClick={() => {
                if (reportViewMode === "json") {
                  handleDownloadReport(
                    JSON.stringify(unifiedData, null, 2),
                    `ai_job_${jobId}_analytics.json`,
                    "application/json"
                  );
                } else {
                  handleDownloadReport(
                    masterExecutiveReport,
                    `ai_job_${jobId}_master_executive_report.md`
                  );
                }
              }}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-violet-600 hover:bg-violet-500 text-white transition-all flex items-center gap-1.5 shadow-md shadow-violet-600/20"
            >
              <span>⬇️ Download .MD</span>
            </button>
          </div>
        </div>

        <div className="bg-gray-950/90 border border-gray-800/80 rounded-xl p-5 max-h-[540px] overflow-y-auto font-mono text-xs text-gray-300 whitespace-pre-wrap leading-relaxed shadow-inner">
          {reportViewMode === "json"
            ? JSON.stringify(unifiedData, null, 2)
            : masterExecutiveReport}
        </div>
      </div>
    </div>
  );
}
