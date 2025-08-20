# ===== controllers/dashboard_controller.py =====
# coding: utf-8

from odoo import http, fields, api
from odoo.http import request
from datetime import datetime, timedelta
import pytz


class DashboardController(http.Controller):

    @http.route('/playstation/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self, period='today'):
        """API endpoint to get dashboard data"""
        data = self._get_dashboard_data(period)
        return data

    @http.route('/playstation/dashboard/action/<string:action_type>', type='json', auth='user')
    def dashboard_action(self, action_type, **kwargs):
        """Handle dashboard actions"""

        if action_type == 'new_session':
            return {
                'type': 'ir.actions.act_window',
                'name': 'New Session',
                'res_model': 'session.session',
                'view_mode': 'form',
                'target': 'new',
            }
        elif action_type == 'new_order':
            return {
                'type': 'ir.actions.act_window',
                'name': 'New Cafe Order',
                'res_model': 'cafe.order',
                'view_mode': 'form',
                'target': 'new',
            }
        elif action_type == 'view_reports':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Session Reports',
                'res_model': 'session.session.report',
                'view_mode': 'pivot,graph,tree',
            }
        elif action_type == 'manage_resources':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Resource Management',
                'res_model': 'room.name',
                'view_mode': 'tree,form',
            }

        return {'error': 'Unknown action'}

    @api.model
    def _get_dashboard_data(self, period='today'):
        """Get dashboard statistics for the specified period"""

        # Calculate date ranges
        today = fields.Date.today()
        now = fields.Datetime.now()

        if period == 'today':
            start_date = today
            end_date = today
            start_datetime = fields.Datetime.to_string(datetime.combine(today, datetime.min.time()))
            end_datetime = fields.Datetime.to_string(datetime.combine(today, datetime.max.time()))
        elif period == 'week':
            start_date = today - timedelta(days=today.weekday())
            end_date = today
            start_datetime = fields.Datetime.to_string(datetime.combine(start_date, datetime.min.time()))
            end_datetime = fields.Datetime.to_string(now)
        elif period == 'month':
            start_date = today.replace(day=1)
            end_date = today
            start_datetime = fields.Datetime.to_string(datetime.combine(start_date, datetime.min.time()))
            end_datetime = fields.Datetime.to_string(now)
        else:
            start_date = today
            end_date = today
            start_datetime = fields.Datetime.to_string(datetime.combine(today, datetime.min.time()))
            end_datetime = fields.Datetime.to_string(datetime.combine(today, datetime.max.time()))

        # Get session statistics
        sessions = request.env['session.session'].search([
            ('starting_time', '>=', start_datetime),
            ('starting_time', '<=', end_datetime)
        ])

        active_sessions = request.env['session.session'].search([
            ('state', '=', 'running')
        ])

        # Get cafe order statistics
        cafe_orders = request.env['cafe.order'].search([
            ('create_date', '>=', start_datetime),
            ('create_date', '<=', end_datetime)
        ])

        # Calculate revenue from both sessions and cafe orders
        total_revenue = 0
        for session in sessions:
            if session.state == 'finished':
                total_revenue += session.total

        for order in cafe_orders:
            if order.state == 'finished':
                total_revenue += order.total

        # Get resource availability
        rooms_data = self._get_rooms_availability()
        consoles_data = self._get_consoles_availability()
        tables_data = self._get_tables_availability()
        cafe_tables_data = self._get_cafe_tables_availability()

        # Get recent activities
        recent_activities = self._get_recent_activities()

        # Revenue chart data
        chart_data = self._get_chart_data(period, start_date, end_date)

        return {
            'stats': {
                'total_sessions': len(sessions),
                'active_sessions': len(active_sessions),
                'cafe_orders': len(cafe_orders),
                'revenue': total_revenue,
            },
            'resources': {
                'rooms': rooms_data,
                'consoles': consoles_data,
                'tables': tables_data,
                'cafe_tables': cafe_tables_data,
            },
            'activities': recent_activities,
            'chart_data': chart_data,
        }

    def _get_rooms_availability(self):
        """Get private rooms availability"""
        rooms = request.env['room.name'].search([])
        occupied_rooms = request.env['session.session'].search([
            ('state', 'in', ['available', 'running']),
            ('session_type', '=', 'private')
        ]).mapped('room_id')

        rooms_data = []
        for room in rooms:
            status = 'occupied' if room in occupied_rooms else 'available'
            rooms_data.append({
                'id': room.id,
                'name': room.name,
                'status': status,
                'type': room.type_id.name if room.type_id else 'N/A'
            })
        return rooms_data

    def _get_consoles_availability(self):
        """Get gaming consoles availability"""
        consoles = request.env['console.number'].search([])
        occupied_consoles = request.env['session.session'].search([
            ('state', 'in', ['available', 'running']),
            ('session_type', '=', 'public'),
            ('individual_type', '=', 'console')
        ]).mapped('console_id')

        consoles_data = []
        for console in consoles:
            status = 'occupied' if console in occupied_consoles else 'available'
            consoles_data.append({
                'id': console.id,
                'name': console.device_num,
                'status': status,
                'type': console.type_id.name if console.type_id else 'N/A'
            })
        return consoles_data

    def _get_tables_availability(self):
        """Get gaming tables availability"""
        tables = request.env['table.tables'].search([])
        occupied_tables = request.env['session.session'].search([
            ('state', 'in', ['available', 'running']),
            ('session_type', '=', 'public'),
            ('individual_type', '=', 'table')
        ]).mapped('table_id')

        tables_data = []
        for table in tables:
            status = 'occupied' if table in occupied_tables else 'available'
            tables_data.append({
                'id': table.id,
                'name': table.table_num,
                'status': status,
                'type': table.type_id.name if table.type_id else 'N/A'
            })
        return tables_data

    def _get_cafe_tables_availability(self):
        """Get cafe tables availability"""
        cafe_tables = request.env['cafe.table'].search([])
        occupied_cafe_tables = request.env['cafe.order'].search([
            ('state', 'in', ['available', 'running'])
        ]).mapped('table_id')

        cafe_tables_data = []
        for table in cafe_tables:
            status = 'occupied' if table in occupied_cafe_tables else 'available'
            cafe_tables_data.append({
                'id': table.id,
                'name': table.table_num,
                'status': status,
            })
        return cafe_tables_data

    def _get_recent_activities(self):
        """Get recent activities from sessions and orders"""
        activities = []

        # Recent sessions
        recent_sessions = request.env['session.session'].search([
            ('starting_time', '>=', fields.Datetime.to_string(datetime.now() - timedelta(hours=2)))
        ], order='starting_time desc', limit=10)
        for session in recent_sessions:
            if session.state == 'running':
                activities.append({
                    'type': 'session_start',
                    'title': f'Session Started - {self._get_session_location(session)}',
                    'time': self._get_time_zone(session.starting_time),
                    'icon': 'fa-play',
                    'color': 'success'
                })
            elif session.state == 'finished':
                activities.append({
                    'type': 'session_end',
                    'title': f'Session Ended - {self._get_session_location(session)}',
                    'time': self._get_time_zone(session.ending_time) or self._get_time_zone(session.starting_time),
                    'icon': 'fa-stop',
                    'color': 'danger'
                })

        # Recent cafe orders
        recent_orders = request.env['cafe.order'].search([
            ('create_date', '>=', fields.Datetime.to_string(datetime.now() - timedelta(hours=2)))
        ], order='create_date desc', limit=5)

        for order in recent_orders:
            activities.append({
                'type': 'cafe_order',
                'title': f'Cafe Order - {order.table_id.table_num if order.table_id else "N/A"}',
                'time': self._get_time_zone(order.create_date),
                'icon': 'fa-coffee',
                'color': 'warning'
            })
        # Sort by time and return latest 10
        activities.sort(key=lambda x: x['time'], reverse=True)
        return activities[:10]

    def _get_session_location(self, session):
        """Get session location string"""
        if session.session_type == 'private' and session.room_id:
            return session.room_id.name
        elif session.session_type == 'public':
            if session.individual_type == 'console' and session.console_id:
                return f"Console {session.console_id.device_num}"
            elif session.individual_type == 'table' and session.table_id:
                return f"Table {session.table_id.table_num}"
        return "Unknown"

    def _get_chart_data(self, period, start_date, end_date):
        """Get chart data for revenue analytics"""
        chart_data = {'labels': [], 'datasets': []}

        if period == 'today':
            # Hourly data for today
            for hour in range(24):
                chart_data['labels'].append(f'{hour:02d}:00')

            # Get hourly revenue
            hourly_revenue = [0] * 24
            sessions = request.env['session.session'].search([
                ('starting_time', '>=', fields.Datetime.to_string(datetime.combine(start_date, datetime.min.time()))),
                ('starting_time', '<=', fields.Datetime.to_string(datetime.combine(start_date, datetime.max.time()))),
                ('state', '=', 'finished')
            ])
            for session in sessions:
                if session.starting_time:
                    starting_time = self._get_time_zone(session.starting_time)
                    hour = starting_time.hour
                    hourly_revenue[hour] += session.total

            chart_data['datasets'] = [{
                'label': 'Revenue',
                'data': hourly_revenue,
                'backgroundColor': 'rgba(102, 126, 234, 0.1)',
                'borderColor': 'rgba(102, 126, 234, 1)',
                'borderWidth': 2,
                'fill': True
            }]

        elif period == 'week':
            # Daily data for week
            current_date = start_date
            daily_revenue = []

            while current_date <= end_date:
                chart_data['labels'].append(current_date.strftime('%a'))

                day_revenue = 0
                sessions = request.env['session.session'].search([
                    ('starting_time', '>=',
                     fields.Datetime.to_string(datetime.combine(current_date, datetime.min.time()))),
                    ('starting_time', '<=',
                     fields.Datetime.to_string(datetime.combine(current_date, datetime.max.time()))),
                    ('state', '=', 'finished')
                ])

                for session in sessions:
                    day_revenue += session.total

                daily_revenue.append(day_revenue)
                current_date += timedelta(days=1)
            print('daily_revenue', daily_revenue)
            chart_data['datasets'] = [{
                'label': 'Daily Revenue',
                'data': daily_revenue,
                'backgroundColor': 'rgba(102, 126, 234, 0.1)',
                'borderColor': 'rgba(102, 126, 234, 1)',
                'borderWidth': 2,
                'fill': True
            }]

        return chart_data

    def _get_time_zone(self, time):
        user_tz = request.env.context.get('tz')
        update_time = pytz.utc.localize(time)
        update_time = update_time.astimezone(pytz.timezone(user_tz))
        update_time = update_time.replace(tzinfo=None)
        return update_time
