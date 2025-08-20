/* ===== static/src/js/dashboard.js ===== */

/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class PlayStationDashboard extends Component {
    static template = "gaming_app.DashboardTemplate";

    setup() {
        this.notification = useService("notification");
        this.action = useService("action");
        this.orm = useService("orm");
        
        this.chartRef = useRef("revenueChart");
        this.chart = null;
        this.refreshInterval = null;

        this.state = useState({
            dashboardData: {},
            currentPeriod: 'today',
            isLoading: false,
        });

        onMounted(() => {
            this.loadDashboardData('today').then(() => {
                this.initChart();
                this.startAutoRefresh();
            });
        });

        onWillUnmount(() => {
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
            if (this.chart) {
                this.chart.destroy();
            }
        });
    }

    async loadDashboardData(period) {
        try {
            const data = await rpc("/playstation/dashboard/data", {
                period: period
            });
            this.state.dashboardData = data;
            return data;
        } catch (error) {
            this.notification.add(_t("Failed to load dashboard data"), {
                type: "danger"
            });
        }
    }

    initChart() {
    const canvas = this.chartRef.el;

    if (canvas && this.state.dashboardData.chart_data) {
        if (this.chart) {
            this.chart.destroy();
        }

        // Set proper canvas dimensions
        const container = canvas.parentElement;
        canvas.width = container.offsetWidth - 50; // Account for padding
        canvas.height = 200;

        this.chart = new Chart(canvas, {
            type: 'line',
            data: this.state.dashboardData.chart_data,
            options: {
                responsive: true,
                maintainAspectRatio: true, // Changed to true
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 4,
                        hoverRadius: 6
                    }
                },
                // Add resize handler
                onResize: (chart, size) => {
                    // Ensure chart resizes properly
                    chart.canvas.style.width = '100%';
                    chart.canvas.style.height = 'auto';
                }
            }
        });
    }
}

    async changeTimeFilter(period) {
        this.state.currentPeriod = period;
        this.state.isLoading = true;
        
        try {
            await this.loadDashboardData(period);
            this.updateChart();
        } finally {
            this.state.isLoading = false;
        }
    }

    async openNewRoom() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Sessions",
            res_model: "session.session",
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
            context: {
                'default_session_type': 'private',
                'default_individual_type': null,
            },
        });
    }

    async openNewConsole() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Console",
            res_model: "session.session",
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
            context: {
                'default_session_type': 'public',
                'default_individual_type': 'console',
            },
        });
    }

    async openNewTable() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Sessions",
            res_model: "session.session",
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
            context: {
                'default_session_type': 'public',
                'default_individual_type': 'table',
            },
        });
    }

    async openNewCafeOrder() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Cafe",
            res_model: "cafe.order",
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
        });
    }

    async getViewReports() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Report",
            res_model: "session.session.report",
            views: [[false, "pivot"], [false, "graph"], [false, "list"]],
            view_mode: "pivot",
            context: {
                'search_default_this_month': 1,
                'search_default_group_by_partner': 1,
            },
        });
    }

    async openSession(roomId) {
        const domain = [["room_id", "=", roomId], ["state", "in", ["running", "available"]]];
        const sessionId = await this.orm.search("session.session", domain, { limit: 1 });
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Sessions",
            res_model: "session.session",
            views: [[false, "form"]],
            view_mode: "form",
            res_id: sessionId[0],
        });
    }

    async openCafe(tableId) {
        const domain = [["table_id", "=", tableId], ["state", "in", ["running", "available"]]];
        const cafeId = await this.orm.search("cafe.order", domain, { limit: 1 });
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Cafe",
            res_model: "cafe.order",
            views: [[false, "form"]],
            view_mode: "form",
            res_id: cafeId[0],
        });
    }

    async openConsole(deviceId) {
        const domain = [["console_id", "=", deviceId], ["state", "in", ["running", "available"]]];
        const consoleSessionId = await this.orm.search("session.session", domain, { limit: 1 });
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Console",
            res_model: "session.session",
            views: [[false, "form"]],
            view_mode: "form",
            res_id: consoleSessionId[0],
        });
    }

    async openTable(tableId) {
        const domain = [["table_id", "=", tableId], ["state", "in", ["running", "available"]]];
        const tableSessionId = await this.orm.search("session.session", domain, { limit: 1 });
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Table",
            res_model: "session.session",
            views: [[false, "form"]],
            view_mode: "form",
            res_id: tableSessionId[0],
        });
    }

    updateChart() {
        if (this.chart && this.state.dashboardData.chart_data) {
            this.chart.data = this.state.dashboardData.chart_data;
            this.chart.update();
        }
    }

    startAutoRefresh() {
        this.refreshInterval = setInterval(async () => {
            await this.loadDashboardData(this.state.currentPeriod);
            this.updateChart();
        }, 3000);
    }

    getTimeAgo(datetime) {
        const now = new Date();
        const time = new Date(datetime);
        const diff = Math.floor((now - time) / 1000);

        if (diff < 60) return _t('Just now');
        if (diff < 3600) return _t('%s minutes ago', Math.floor(diff / 60));
        if (diff < 86400) return _t('%s hours ago', Math.floor(diff / 3600));
        return _t('%s days ago', Math.floor(diff / 86400));
    }

    formatNumber(num) {
        return new Intl.NumberFormat().format(num);
    }

    get stats() {
        return this.state.dashboardData.stats || {};
    }

    get activities() {
        return this.state.dashboardData.activities || [];
    }

    get resources() {
        return this.state.dashboardData.resources || {};
    }

    get chartData() {
        return this.state.dashboardData.chart_data;
    }

    getResourceStatusClass(status) {
        return status === 'available' ? 'status-available' : 'status-occupied';
    }

    getResourceStatusText(status) {
        return status === 'available' ? _t('Available') : _t('Occupied');
    }
}

registry.category("actions").add("playstation_dashboard", PlayStationDashboard);
