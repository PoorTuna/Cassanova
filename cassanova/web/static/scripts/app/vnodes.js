// -------------------------
// Constants
// -------------------------
const TOKEN_MIN = -9223372036854775808n;
const TOKEN_MAX = 9223372036854775807n;
const TOKEN_RANGE = TOKEN_MAX - TOKEN_MIN;

// -------------------------
// Flatten vnodes
// -------------------------
let vnodes = [];
clusterData.forEach((node, idx) => {
    node.tokens.forEach((t, v) => vnodes.push({
        token: BigInt(t),
        nodeIdx: idx,
        vnodeIdx: v,
        host_id: node.host_id,
        address: node.address
    }));
});
vnodes.sort((a, b) => a.token < b.token ? -1 : 1);

function tokenToFrac(tok) {
    return Number(tok - TOKEN_MIN) / Number(TOKEN_RANGE + 1n);
}

function arcFraction(startTok, endTok) {
    if (endTok >= startTok) return Number(endTok - startTok) / Number(TOKEN_RANGE + 1n);
    return Number(TOKEN_MAX - startTok + endTok - TOKEN_MIN + 1n) / Number(TOKEN_RANGE + 1n);
}

const ranges = [];
for (let i = 0; i < vnodes.length; i++) {
    const cur = vnodes[i], next = vnodes[(i + 1) % vnodes.length];
    const fracStart = tokenToFrac(cur.token);
    const fracEnd = fracStart + arcFraction(cur.token, next.token);
    ranges.push({...cur, startAngle: fracStart * 2 * Math.PI, endAngle: fracEnd * 2 * Math.PI});
}

// -------------------------
// D3 Visualization
// -------------------------
window.addEventListener("DOMContentLoaded", () => {
    const svg = d3.select("#viz svg");
    const width = svg.node().clientWidth;
    const height = svg.node().clientHeight;
    const centerX = width / 2, centerY = height / 2;
    const OUTER = Math.min(width, height) * 0.42;
    const INNER = OUTER - OUTER * 0.18;
    const arcGen = d3.arc()
        .innerRadius(INNER)
        .outerRadius(OUTER)
        .startAngle(d => d.startAngle)
        .endAngle(d => d.endAngle);

    // Theme colors
    const theme = getComputedStyle(document.documentElement);
    const basePalette = [
        theme.getPropertyValue('--color-primary').trim(),
        theme.getPropertyValue('--color-primary-hover').trim(),
        theme.getPropertyValue('--color-primary-active').trim(),
        theme.getPropertyValue('--color-primary-light').trim(),
        theme.getPropertyValue('--color-primary-strong').trim()
    ];
    const strokeColor = theme.getPropertyValue('--bg-hover').trim();

    function nodeColor(idx, vnodeIdx) {
        const base = d3.hsl(basePalette[idx % basePalette.length]);
        const nodeVnodes = vnodes.filter(v => v.nodeIdx === idx).length;
        const offset = (vnodeIdx / nodeVnodes) * 30;
        base.h = (base.h + offset) % 360;
        return base.formatHex();
    }

    const rootG = svg.append("g").attr("transform", `translate(${centerX},${centerY})`);
    rootG.append("circle")
        .attr("r", (OUTER + INNER) / 2)
        .attr("fill", "none")
        .attr("stroke", strokeColor)
        .attr("stroke-width", 2);

    let selectedNodeIdx = null;
    const tooltip = d3.select("#viz")
        .append("div")
        .attr("class", "token-tooltip");

    const arcs = rootG.selectAll("path.arc")
        .data(ranges)
        .enter()
        .append("path")
        .attr("class", "arc")
        .attr("d", arcGen)
        .attr("fill", d => nodeColor(d.nodeIdx, d.vnodeIdx))
        .attr("stroke", "rgba(0,0,0,0.3)")
        .attr("stroke-width", 0.4)
        .on("mouseover", (e, d) => {
            d3.select(e.currentTarget).classed("hovered", true);
            tooltip
                .html(`
                    <b>Token:</b> ${d.token}<br/>
                    <b>Node:</b> ${d.host_id}<br/>
                    <b>IP:</b> ${d.address}
                `)
                .classed("show", true);
        })
        .on("mousemove", (e) => {
            tooltip
                .style("left", `${e.pageX}px`)
                .style("top", `${e.pageY - 10}px`);
        })
        .on("mouseout", (e) => {
            d3.select(e.currentTarget).classed("hovered", false);
            tooltip.classed("show", false);
        })
        .on("click", (e, d) => {
            selectedNodeIdx = (selectedNodeIdx === d.nodeIdx) ? null : d.nodeIdx;
            highlightNode(selectedNodeIdx);
            const row = document.querySelector(`#node-${selectedNodeIdx}`);
            if (row) row.scrollIntoView({behavior: 'smooth', block: 'center'});
        });

    // -------------------------
    // Node Menu
    // -------------------------
    const menu = d3.select("#menu-scroll");
    clusterData.forEach((node, i) => {
        const section = menu.append("div")
            .attr("class", "node-section")
            .attr("id", `node-${i}`);
        const header = section.append("div")
            .attr("class", "node-header")
            .style("color", nodeColor(i, 0))
            .text(`${node.address} (${node.host_id})`);
        const ul = section.append("ul").attr("class", "vnode-list");
        node.tokens.forEach(t => ul.append("li").text(`Token: ${t}`));

        header.on("mouseover", () => arcs.filter(d => d.nodeIdx === i).classed("hovered", true))
            .on("mouseout", () => arcs.filter(d => d.nodeIdx === i).classed("hovered", false))
            .on("click", () => {
                selectedNodeIdx = (selectedNodeIdx === i) ? null : i;
                highlightNode(selectedNodeIdx);
                if (selectedNodeIdx !== null) section.node().scrollIntoView({behavior: 'smooth', block: 'center'});
            });
    });

    function highlightNode(idx) {
        if (idx === null) {
            arcs.classed("highlight", false).classed("dim", false);
            d3.selectAll(".vnode-list li").classed("highlight", false);
            return;
        }
        arcs.classed("dim", d => d.nodeIdx !== idx);
        arcs.classed("highlight", d => d.nodeIdx === idx);
        d3.selectAll(".vnode-list li").classed("highlight", false);
        const nodeSection = document.querySelector(`#node-${idx}`);
        if (nodeSection) nodeSection.querySelectorAll(".vnode-list li").forEach(li => li.classList.add("highlight"));
    }

    const zoom = d3.zoom()
        .scaleExtent([0.2, 6])
        .on("zoom", event => {
            rootG.attr("transform", `translate(${centerX},${centerY}) scale(${event.transform.k})`);
        });
    svg.call(zoom).on("dblclick.zoom", null);

    const filterInput = document.getElementById("node-filter");
    filterInput.addEventListener("input", () => {
        const query = filterInput.value.toLowerCase().trim();
        clusterData.forEach((node, i) => {
            const section = document.querySelector(`#node-${i}`);
            if (!section) return;
            const matchNode = node.host_id.toLowerCase().includes(query) ||
                node.address.toLowerCase().includes(query);
            const matchToken = node.tokens.some(t => t.toString().includes(query));
            section.style.display = (query === "" || matchNode || matchToken) ? "" : "none";
        });
    });
});
