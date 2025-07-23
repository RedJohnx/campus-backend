"""
Dashboard and Analytics module for Campus Assets system.
Provides comprehensive statistics, analytics, and chart data for management insights.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import logging
from bson import ObjectId
from database import get_db
from auth import require_auth, require_role
import calendar
# Replace the datetime imports in dashboard.py with:
from datetime import datetime, timedelta
import time  # Add this if you need time operations
# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
dashboard_bp = Blueprint('dashboard', __name__)

# ============================================================================
# MAIN DASHBOARD OVERVIEW
# ============================================================================

@dashboard_bp.route('/overview', methods=['GET'])
@require_auth
def get_dashboard_overview():
    """
    Get comprehensive dashboard overview with key metrics.
    """
    try:
        db = get_db()
        
        # Get basic counts
        total_resources = db.resources.count_documents({})
        total_departments = db.departments.count_documents({})
        total_users = db.users.count_documents({})
        
        # Calculate total asset value and quantity
        asset_pipeline = [
            {'$group': {
                '_id': None,
                'total_value': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'total_quantity': {'$sum': '$quantity'},
                'avg_cost': {'$avg': '$cost'},
                'max_cost': {'$max': '$cost'},
                'min_cost': {'$min': '$cost'}
            }}
        ]
        
        asset_stats = list(db.resources.aggregate(asset_pipeline))
        
        if asset_stats:
            financial_metrics = asset_stats[0]
            total_value = financial_metrics['total_value']
            total_quantity = financial_metrics['total_quantity']
            avg_cost = financial_metrics['avg_cost']
            max_cost = financial_metrics['max_cost']
            min_cost = financial_metrics['min_cost']
        else:
            total_value = total_quantity = avg_cost = max_cost = min_cost = 0
        
        # Recent activity (last 30 days)
        recent_date = datetime.now() - timedelta(days=30)
        recent_additions = db.resources.count_documents({
            'created_at': {'$gte': recent_date}
        })
        
        # Top department by resources
        top_department = list(db.resources.aggregate([
            {'$group': {
                '_id': '$department',
                'resource_count': {'$sum': '$quantity'}
            }},
            {'$sort': {'resource_count': -1}},
            {'$limit': 1}
        ]))
        
        top_dept_name = top_department[0]['_id'] if top_department else 'N/A'
        top_dept_count = top_department[0]['resource_count'] if top_department else 0
        
        # Most expensive item
        most_expensive = db.resources.find_one(
            {},
            sort=[('cost', -1)]
        )
        
        # Device type diversity
        unique_devices = len(db.resources.distinct('device_name'))
        unique_locations = len(db.resources.distinct('location'))
        
        # Resource utilization metrics
        utilization_stats = calculate_utilization_metrics()
        
        return jsonify({
            'overview': {
                'total_resources': total_resources,
                'total_departments': total_departments,
                'total_users': total_users,
                'total_value': total_value,
                'total_quantity': total_quantity,
                'unique_devices': unique_devices,
                'unique_locations': unique_locations,
                'recent_additions_30d': recent_additions
            },
            'financial_metrics': {
                'total_asset_value': total_value,
                'average_cost_per_item': avg_cost,
                'most_expensive_item': max_cost,
                'least_expensive_item': min_cost,
                'cost_per_resource': total_value / total_resources if total_resources > 0 else 0
            },
            'top_performers': {
                'leading_department': {
                    'name': top_dept_name,
                    'resource_count': top_dept_count
                },
                'most_expensive_item': {
                    'device_name': most_expensive.get('device_name', 'N/A') if most_expensive else 'N/A',
                    'cost': most_expensive.get('cost', 0) if most_expensive else 0,
                    'department': most_expensive.get('department', 'N/A') if most_expensive else 'N/A'
                }
            },
            'utilization_metrics': utilization_stats,
            'generated_at': datetime.now().isoformat(),
            'data_freshness': {
                'last_updated': datetime.now().isoformat(),
                'cache_duration': '5 minutes',
                'next_refresh': (datetime.now() + timedelta(minutes=5)).isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating dashboard overview: {e}")
        return jsonify({'error': 'Failed to generate dashboard overview'}), 500

# ============================================================================
# DEPARTMENT ANALYTICS
# ============================================================================

@dashboard_bp.route('/department-analytics', methods=['GET'])
@require_auth
def get_department_analytics():
    """
    Get detailed analytics for all departments.
    """
    try:
        db = get_db()
        
        # Department-wise resource breakdown
        dept_pipeline = [
            {'$group': {
                '_id': '$department',
                'total_resources': {'$sum': '$quantity'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'unique_devices': {'$addToSet': '$device_name'},
                'unique_locations': {'$addToSet': '$location'},
                'avg_cost_per_item': {'$avg': '$cost'},
                'max_cost_item': {'$max': '$cost'},
                'latest_procurement': {'$max': '$procurement_date'},
                'oldest_procurement': {'$min': '$procurement_date'}
            }},
            {'$sort': {'total_cost': -1}}
        ]
        
        dept_analytics = list(db.resources.aggregate(dept_pipeline))
        
        # Enhanced department data
        enhanced_departments = []
        total_system_cost = sum(dept['total_cost'] for dept in dept_analytics)
        
        for dept in dept_analytics:
            dept_name = dept['_id']
            
            # Calculate department efficiency metrics
            efficiency_metrics = calculate_department_efficiency(dept_name)
            
            # Cost distribution analysis
            cost_percentage = (dept['total_cost'] / total_system_cost * 100) if total_system_cost > 0 else 0
            
            enhanced_dept = {
                'department_name': dept_name,
                'metrics': {
                    'total_resources': dept['total_resources'],
                    'total_cost': dept['total_cost'],
                    'unique_devices': len(dept['unique_devices']),
                    'unique_locations': len(dept['unique_locations']),
                    'avg_cost_per_item': dept['avg_cost_per_item'],
                    'max_cost_item': dept['max_cost_item'],
                    'cost_percentage_of_total': cost_percentage
                },
                'timeline': {
                    'latest_procurement': dept['latest_procurement'].isoformat() if dept['latest_procurement'] else None,
                    'oldest_procurement': dept['oldest_procurement'].isoformat() if dept['oldest_procurement'] else None,
                    'procurement_span_days': (dept['latest_procurement'] - dept['oldest_procurement']).days if dept['latest_procurement'] and dept['oldest_procurement'] else 0
                },
                'efficiency': efficiency_metrics,
                'device_types': dept['unique_devices'][:10],  # Top 10 device types
                'locations': dept['unique_locations'][:10]     # Top 10 locations
            }
            
            enhanced_departments.append(enhanced_dept)
        
        # System-wide department comparison
        comparison_metrics = {
            'highest_value_department': max(enhanced_departments, key=lambda x: x['metrics']['total_cost'])['department_name'] if enhanced_departments else 'N/A',
            'most_diverse_department': max(enhanced_departments, key=lambda x: x['metrics']['unique_devices'])['department_name'] if enhanced_departments else 'N/A',
            'most_distributed_department': max(enhanced_departments, key=lambda x: x['metrics']['unique_locations'])['department_name'] if enhanced_departments else 'N/A',
            'average_cost_per_department': total_system_cost / len(enhanced_departments) if enhanced_departments else 0
        }
        
        return jsonify({
            'department_analytics': enhanced_departments,
            'summary': {
                'total_departments': len(enhanced_departments),
                'total_system_value': total_system_cost,
                'average_resources_per_dept': sum(dept['metrics']['total_resources'] for dept in enhanced_departments) / len(enhanced_departments) if enhanced_departments else 0,
                'comparison_metrics': comparison_metrics
            },
            'generated_at': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating department analytics: {e}")
        return jsonify({'error': 'Failed to generate department analytics'}), 500

# ============================================================================
# COST ANALYSIS
# ============================================================================

@dashboard_bp.route('/cost-analysis', methods=['GET'])
@require_auth
def get_cost_analysis():
    """
    Get comprehensive cost analysis and financial insights.
    """
    try:
        db = get_db()
        
        # Time-based cost analysis
        time_range = request.args.get('time_range', '12_months')  # 12_months, 6_months, 3_months, 1_month
        
        cost_trends = generate_cost_trends(time_range)
        
        # Cost distribution by device type
        device_cost_pipeline = [
            {'$group': {
                '_id': '$device_name',
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'total_quantity': {'$sum': '$quantity'},
                'avg_unit_cost': {'$avg': '$cost'},
                'resource_count': {'$sum': 1}
            }},
            {'$sort': {'total_cost': -1}},
            {'$limit': 15}
        ]
        
        device_costs = list(db.resources.aggregate(device_cost_pipeline))
        
        # Cost distribution by location
        location_cost_pipeline = [
            {'$group': {
                '_id': '$location',
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'department': {'$first': '$department'},
                'resource_count': {'$sum': '$quantity'}
            }},
            {'$sort': {'total_cost': -1}},
            {'$limit': 20}
        ]
        
        location_costs = list(db.resources.aggregate(location_cost_pipeline))
        
        # Budget allocation insights
        budget_insights = calculate_budget_insights()
        
        # ROI and efficiency metrics
        roi_metrics = calculate_roi_metrics()
        
        # Cost category analysis
        cost_categories = {
            'high_value_items': list(db.resources.find({'cost': {'$gte': 100000}}).sort('cost', -1).limit(10)),
            'medium_value_items': db.resources.count_documents({'cost': {'$gte': 50000, '$lt': 100000}}),
            'low_value_items': db.resources.count_documents({'cost': {'$lt': 50000}}),
            'bulk_purchases': list(db.resources.find({'quantity': {'$gte': 10}}).sort('quantity', -1).limit(10))
        }
        
        # Convert ObjectIds in high_value_items and bulk_purchases
        for item in cost_categories['high_value_items']:
            item['_id'] = str(item['_id'])
        for item in cost_categories['bulk_purchases']:
            item['_id'] = str(item['_id'])
        
        return jsonify({
            'cost_analysis': {
                'trends': cost_trends,
                'device_type_costs': device_costs,
                'location_costs': location_costs,
                'categories': cost_categories
            },
            'budget_insights': budget_insights,
            'roi_metrics': roi_metrics,
            'financial_summary': {
                'total_invested': sum(item['total_cost'] for item in device_costs),
                'average_cost_per_device_type': sum(item['avg_unit_cost'] for item in device_costs) / len(device_costs) if device_costs else 0,
                'cost_efficiency_score': calculate_cost_efficiency_score(),
                'budget_utilization_rate': calculate_budget_utilization()
            },
            'generated_at': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating cost analysis: {e}")
        return jsonify({'error': 'Failed to generate cost analysis'}), 500

# ============================================================================
# UTILIZATION METRICS
# ============================================================================

@dashboard_bp.route('/utilization-metrics', methods=['GET'])
@require_auth
def get_utilization_metrics():
    """
    Get resource utilization and efficiency metrics.
    """
    try:
        db = get_db()
        
        # Resource density analysis
        density_pipeline = [
            {'$group': {
                '_id': '$location',
                'resource_count': {'$sum': '$quantity'},
                'unique_devices': {'$addToSet': '$device_name'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'department': {'$first': '$department'}
            }},
            {'$addFields': {
                'device_diversity': {'$size': '$unique_devices'},
                'cost_per_resource': {'$divide': ['$total_cost', '$resource_count']}
            }},
            {'$sort': {'resource_count': -1}}
        ]
        
        location_density = list(db.resources.aggregate(density_pipeline))
        
        # Device utilization patterns
        device_utilization = analyze_device_utilization()
        
        # Age and maintenance insights
        age_analysis = analyze_equipment_age()
        
        # Space utilization efficiency
        space_efficiency = calculate_space_efficiency()
        
        # Procurement patterns
        procurement_patterns = analyze_procurement_patterns()
        
        # Utilization scoring
        utilization_scores = {
            'overall_efficiency': calculate_overall_efficiency(),
            'resource_distribution_score': calculate_distribution_score(),
            'cost_optimization_score': calculate_cost_optimization(),
            'maintenance_readiness_score': calculate_maintenance_readiness()
        }
        
        return jsonify({
            'utilization_metrics': {
                'location_density': location_density,
                'device_utilization': device_utilization,
                'age_analysis': age_analysis,
                'space_efficiency': space_efficiency,
                'procurement_patterns': procurement_patterns
            },
            'efficiency_scores': utilization_scores,
            'recommendations': generate_utilization_recommendations(location_density, device_utilization),
            'generated_at': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating utilization metrics: {e}")
        return jsonify({'error': 'Failed to generate utilization metrics'}), 500

# ============================================================================
# CHART DATA GENERATION
# ============================================================================

@dashboard_bp.route('/charts', methods=['GET'])
@require_auth
def get_chart_data():
    """
    Generate chart data for frontend visualizations.
    """
    try:
        chart_type = request.args.get('type', 'all')  # all, pie, bar, line, donut
        
        chart_data = {}
        
        if chart_type in ['all', 'pie']:
            # Department distribution by asset count (quantity)
            chart_data['department_distribution'] = generate_pie_chart_data('department', 'quantity')
            # Department distribution by cost
            chart_data['department_cost_pie'] = generate_pie_chart_data('department', 'cost')
            # Device type distribution
            chart_data['device_type_pie'] = generate_pie_chart_data('device_name', 'quantity')
        
        if chart_type in ['all', 'bar']:
            chart_data['location_resource_bar'] = generate_bar_chart_data('location', 'quantity')
            chart_data['department_resource_bar'] = generate_bar_chart_data('department', 'quantity')
        
        if chart_type in ['all', 'line']:
            chart_data['procurement_timeline'] = generate_line_chart_data('procurement_date', 'cost')
            chart_data['cost_trends'] = generate_monthly_cost_trends()
        
        if chart_type in ['all', 'donut']:
            chart_data['cost_category_donut'] = generate_cost_category_donut()
            chart_data['location_distribution_donut'] = generate_location_distribution_donut()
        
        # Heat map data for resource density
        if chart_type in ['all', 'heatmap']:
            chart_data['resource_density_heatmap'] = generate_heatmap_data()
        
        return jsonify({
            'charts': chart_data,
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'chart_types_available': ['pie', 'bar', 'line', 'donut', 'heatmap'],
                'data_points': sum(len(data.get('data', [])) for data in chart_data.values() if isinstance(data, dict)),
                'total_charts': len(chart_data)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating chart data: {e}")
        return jsonify({'error': 'Failed to generate chart data'}), 500

# ============================================================================
# UTILITY FUNCTIONS FOR ANALYTICS
# ============================================================================

def calculate_utilization_metrics():
    """Calculate resource utilization metrics."""
    try:
        db = get_db()
        
        # Resources per location analysis
        location_stats = list(db.resources.aggregate([
            {'$group': {
                '_id': '$location',
                'resource_count': {'$sum': '$quantity'},
                'unique_devices': {'$addToSet': '$device_name'}
            }},
            {'$addFields': {
                'device_diversity': {'$size': '$unique_devices'}
            }}
        ]))
        
        if location_stats:
            avg_resources_per_location = sum(loc['resource_count'] for loc in location_stats) / len(location_stats)
            max_resources_location = max(location_stats, key=lambda x: x['resource_count'])
            max_diversity_location = max(location_stats, key=lambda x: x['device_diversity'])
            
            return {
                'total_locations': len(location_stats),
                'avg_resources_per_location': avg_resources_per_location,
                'most_resourced_location': {
                    'name': max_resources_location['_id'],
                    'resource_count': max_resources_location['resource_count']
                },
                'most_diverse_location': {
                    'name': max_diversity_location['_id'],
                    'device_types': max_diversity_location['device_diversity']
                }
            }
        else:
            return {
                'total_locations': 0,
                'avg_resources_per_location': 0,
                'most_resourced_location': None,
                'most_diverse_location': None
            }
            
    except Exception as e:
        logger.error(f"Error calculating utilization metrics: {e}")
        return {}

def calculate_department_efficiency(department_name):
    """Calculate efficiency metrics for a specific department."""
    try:
        db = get_db()
        
        # Department-specific calculations
        dept_resources = list(db.resources.find({'department': department_name}))
        
        if not dept_resources:
            return {'efficiency_score': 0, 'utilization_rate': 0}
        
        total_cost = sum(r['cost'] * r['quantity'] for r in dept_resources)
        total_quantity = sum(r['quantity'] for r in dept_resources)
        unique_locations = len(set(r['location'] for r in dept_resources))
        unique_devices = len(set(r['device_name'] for r in dept_resources))
        
        # Efficiency scoring (0-100)
        cost_efficiency = min(100, (total_cost / 1000000) * 10) if total_cost > 0 else 0
        diversity_score = min(100, (unique_devices / 20) * 100)
        distribution_score = min(100, (unique_locations / 10) * 100)
        
        overall_efficiency = (cost_efficiency + diversity_score + distribution_score) / 3
        
        return {
            'efficiency_score': round(overall_efficiency, 2),
            'cost_efficiency': round(cost_efficiency, 2),
            'diversity_score': round(diversity_score, 2),
            'distribution_score': round(distribution_score, 2),
            'utilization_rate': round((total_quantity / (unique_locations * 10)) * 100, 2) if unique_locations > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error calculating department efficiency: {e}")
        return {'efficiency_score': 0}

def generate_cost_trends(time_range):
    """Generate cost trends over specified time period."""
    try:
        db = get_db()
        
        # Define time range
        end_date = datetime.now()
        if time_range == '1_month':
            start_date = end_date - timedelta(days=30)
            group_by = {'$dateToString': {'format': '%Y-%m-%d', 'date': '$procurement_date'}}
        elif time_range == '3_months':
            start_date = end_date - timedelta(days=90)
            group_by = {'$dateToString': {'format': '%Y-%U', 'date': '$procurement_date'}}
        elif time_range == '6_months':
            start_date = end_date - timedelta(days=180)
            group_by = {'$dateToString': {'format': '%Y-%m', 'date': '$procurement_date'}}
        else:  # 12_months
            start_date = end_date - timedelta(days=365)
            group_by = {'$dateToString': {'format': '%Y-%m', 'date': '$procurement_date'}}
        
        trends_pipeline = [
            {'$match': {
                'procurement_date': {'$gte': start_date, '$lte': end_date}
            }},
            {'$group': {
                '_id': group_by,
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'resource_count': {'$sum': '$quantity'},
                'unique_devices': {'$addToSet': '$device_name'}
            }},
            {'$sort': {'_id': 1}}
        ]
        
        trends = list(db.resources.aggregate(trends_pipeline))
        
        return {
            'period': time_range,
            'data_points': len(trends),
            'trends': trends,
            'total_cost_in_period': sum(t['total_cost'] for t in trends),
            'total_resources_in_period': sum(t['resource_count'] for t in trends)
        }
        
    except Exception as e:
        logger.error(f"Error generating cost trends: {e}")
        return {'period': time_range, 'data_points': 0, 'trends': []}

def generate_pie_chart_data(group_field, value_field):
    """Generate pie chart data for specified grouping."""
    try:
        db = get_db()
        
        if value_field == 'cost':
            value_expr = {'$sum': {'$multiply': ['$cost', '$quantity']}}
        elif value_field == 'quantity':
            value_expr = {'$sum': '$quantity'}
        else:
            value_expr = {'$sum': f'${value_field}'}
        
        pipeline = [
            {'$group': {
                '_id': f'${group_field}',
                'value': value_expr
            }},
            {'$sort': {'value': -1}},
            {'$limit': 15}  # Increased limit for more departments
        ]
        
        data = list(db.resources.aggregate(pipeline))
        
        # Ensure we have data
        if not data:
            logger.warning(f"No data found for pie chart: {group_field} by {value_field}")
            return {'labels': [], 'data': [], 'total': 0, 'type': 'pie'}
        
        return {
            'labels': [item['_id'] for item in data],
            'data': [item['value'] for item in data],
            'total': sum(item['value'] for item in data),
            'type': 'pie',
            'count': len(data)
        }
        
    except Exception as e:
        logger.error(f"Error generating pie chart data: {e}")
        return {'labels': [], 'data': [], 'total': 0, 'type': 'pie'}

def generate_bar_chart_data(group_field, value_field):
    """Generate bar chart data for specified grouping."""
    try:
        db = get_db()
        
        if value_field == 'cost':
            value_expr = {'$sum': {'$multiply': ['$cost', '$quantity']}}
        else:
            value_expr = {'$sum': f'${value_field}'}
        
        pipeline = [
            {'$group': {
                '_id': f'${group_field}',
                'value': value_expr
            }},
            {'$sort': {'value': -1}},
            {'$limit': 15}
        ]
        
        data = list(db.resources.aggregate(pipeline))
        
        return {
            'categories': [item['_id'] for item in data],
            'series': [{
                'name': value_field.title(),
                'data': [item['value'] for item in data]
            }],
            'type': 'bar'
        }
        
    except Exception as e:
        logger.error(f"Error generating bar chart data: {e}")
        return {'categories': [], 'series': [], 'type': 'bar'}

def generate_line_chart_data(date_field, value_field):
    """Generate line chart data for time series."""
    try:
        db = get_db()
        
        # Get last 12 months of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        if value_field == 'cost':
            value_expr = {'$sum': {'$multiply': ['$cost', '$quantity']}}
        else:
            value_expr = {'$sum': f'${value_field}'}
        
        pipeline = [
            {'$match': {
                date_field: {'$gte': start_date, '$lte': end_date}
            }},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m', 'date': f'${date_field}'}},
                'value': value_expr
            }},
            {'$sort': {'_id': 1}}
        ]
        
        data = list(db.resources.aggregate(pipeline))
        
        return {
            'categories': [item['_id'] for item in data],
            'series': [{
                'name': value_field.title(),
                'data': [item['value'] for item in data]
            }],
            'type': 'line'
        }
        
    except Exception as e:
        logger.error(f"Error generating line chart data: {e}")
        return {'categories': [], 'series': [], 'type': 'line'}

def calculate_budget_insights():
    """Calculate budget allocation and insights."""
    try:
        db = get_db()
        
        total_budget = db.resources.aggregate([
            {'$group': {'_id': None, 'total': {'$sum': {'$multiply': ['$cost', '$quantity']}}}}
        ])
        total_budget = list(total_budget)[0]['total'] if list(total_budget) else 0
        
        # Budget allocation by department
        dept_allocation = list(db.resources.aggregate([
            {'$group': {
                '_id': '$department',
                'allocated_budget': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'resource_count': {'$sum': '$quantity'}
            }},
            {'$addFields': {
                'percentage': {'$multiply': [{'$divide': ['$allocated_budget', total_budget]}, 100]}
            }},
            {'$sort': {'allocated_budget': -1}}
        ]))
        
        return {
            'total_budget': total_budget,
            'department_allocation': dept_allocation,
            'budget_distribution': {
                'high_budget_departments': [d for d in dept_allocation if d['percentage'] > 20],
                'medium_budget_departments': [d for d in dept_allocation if 5 <= d['percentage'] <= 20],
                'low_budget_departments': [d for d in dept_allocation if d['percentage'] < 5]
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating budget insights: {e}")
        return {}

def calculate_roi_metrics():
    """Calculate ROI and efficiency metrics."""
    try:
        db = get_db()
        
        # Calculate ROI based on equipment age and usage
        current_date = datetime.time.now()
        
        roi_pipeline = [
            {'$addFields': {
                'age_days': {'$subtract': [current_date, '$procurement_date']},
                'total_investment': {'$multiply': ['$cost', '$quantity']}
            }},
            {'$group': {
                '_id': '$department',
                'total_investment': {'$sum': '$total_investment'},
                'avg_age_days': {'$avg': '$age_days'},
                'resource_count': {'$sum': '$quantity'}
            }},
            {'$addFields': {
                'estimated_daily_value': {'$divide': ['$total_investment', '$avg_age_days']},
                'roi_score': {'$multiply': [{'$divide': ['$resource_count', '$total_investment']}, 1000000]}
            }}
        ]
        
        roi_data = list(db.resources.aggregate(roi_pipeline))
        
        return {
            'department_roi': roi_data,
            'overall_roi_score': sum(d['roi_score'] for d in roi_data) / len(roi_data) if roi_data else 0,
            'best_performing_department': max(roi_data, key=lambda x: x['roi_score'])['_id'] if roi_data else 'N/A'
        }
        
    except Exception as e:
        logger.error(f"Error calculating ROI metrics: {e}")
        return {}

# Additional utility functions for various calculations
def analyze_device_utilization():
    """Analyze device utilization patterns."""
    try:
        db = get_db()
        
        utilization_pipeline = [
            {'$group': {
                '_id': '$device_name',
                'total_quantity': {'$sum': '$quantity'},
                'locations_used': {'$addToSet': '$location'},
                'departments_used': {'$addToSet': '$department'},
                'avg_cost': {'$avg': '$cost'}
            }},
            {'$addFields': {
                'location_spread': {'$size': '$locations_used'},
                'department_spread': {'$size': '$departments_used'}
            }},
            {'$sort': {'total_quantity': -1}}
        ]
        
        return list(db.resources.aggregate(utilization_pipeline))
        
    except Exception as e:
        logger.error(f"Error analyzing device utilization: {e}")
        return []

def analyze_equipment_age():
    """Analyze equipment age and maintenance needs."""
    try:
        db = get_db()
        current_date = datetime.time.now()
        
        age_pipeline = [
            {'$addFields': {
                'age_days': {'$divide': [{'$subtract': [current_date, '$procurement_date']}, 86400000]}
            }},
            {'$group': {
                '_id': {
                    '$switch': {
                        'branches': [
                            {'case': {'$lt': ['$age_days', 365]}, 'then': 'New (< 1 year)'},
                            {'case': {'$lt': ['$age_days', 1095]}, 'then': 'Recent (1-3 years)'},
                            {'case': {'$lt': ['$age_days', 1825]}, 'then': 'Mature (3-5 years)'},
                            {'case': {'$gte': ['$age_days', 1825]}, 'then': 'Old (> 5 years)'}
                        ],
                        'default': 'Unknown'
                    }
                },
                'count': {'$sum': '$quantity'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}}
            }}
        ]
        
        return list(db.resources.aggregate(age_pipeline))
        
    except Exception as e:
        logger.error(f"Error analyzing equipment age: {e}")
        return []

def calculate_space_efficiency():
    """Calculate space utilization efficiency."""
    try:
        db = get_db()
        
        space_pipeline = [
            {'$group': {
                '_id': '$location',
                'resource_density': {'$sum': '$quantity'},
                'cost_density': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'device_variety': {'$addToSet': '$device_name'}
            }},
            {'$addFields': {
                'efficiency_score': {
                    '$add': [
                        {'$multiply': [{'$size': '$device_variety'}, 10]},
                        {'$multiply': ['$resource_density', 2]}
                    ]
                }
            }},
            {'$sort': {'efficiency_score': -1}}
        ]
        
        return list(db.resources.aggregate(space_pipeline))
        
    except Exception as e:
        logger.error(f"Error calculating space efficiency: {e}")
        return []

def analyze_procurement_patterns():
    """Analyze procurement patterns and trends."""
    try:
        db = get_db()
        
        pattern_pipeline = [
            {'$group': {
                '_id': {
                    'year': {'$year': '$procurement_date'},
                    'month': {'$month': '$procurement_date'}
                },
                'items_procured': {'$sum': '$quantity'},
                'total_spent': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'unique_devices': {'$addToSet': '$device_name'}
            }},
            {'$sort': {'_id.year': -1, '_id.month': -1}},
            {'$limit': 24}  # Last 24 months
        ]
        
        return list(db.resources.aggregate(pattern_pipeline))
        
    except Exception as e:
        logger.error(f"Error analyzing procurement patterns: {e}")
        return []

# Scoring and efficiency calculation functions
def calculate_overall_efficiency():
    """Calculate overall system efficiency score."""
    try:
        db = get_db()
        
        # Multiple factors contribute to efficiency
        total_resources = db.resources.count_documents({})
        total_locations = len(db.resources.distinct('location'))
        total_departments = len(db.resources.distinct('department'))
        
        if total_locations == 0 or total_departments == 0:
            return 0
        
        # Efficiency factors
        resource_distribution = total_resources / total_locations
        departmental_spread = total_locations / total_departments
        
        # Normalize to 0-100 scale
        efficiency_score = min(100, (resource_distribution * departmental_spread) / 10)
        
        return round(efficiency_score, 2)
        
    except Exception as e:
        logger.error(f"Error calculating overall efficiency: {e}")
        return 0

def calculate_distribution_score():
    """Calculate resource distribution score."""
    try:
        db = get_db()
        
        distribution_pipeline = [
            {'$group': {
                '_id': '$department',
                'locations': {'$addToSet': '$location'},
                'resources': {'$sum': '$quantity'}
            }},
            {'$addFields': {
                'location_count': {'$size': '$locations'},
                'resources_per_location': {'$divide': ['$resources', {'$size': '$locations'}]}
            }}
        ]
        
        dept_distributions = list(db.resources.aggregate(distribution_pipeline))
        
        if not dept_distributions:
            return 0
        
        # Calculate average distribution efficiency
        avg_efficiency = sum(d['resources_per_location'] for d in dept_distributions) / len(dept_distributions)
        
        # Normalize to 0-100 scale
        distribution_score = min(100, avg_efficiency * 2)
        
        return round(distribution_score, 2)
        
    except Exception as e:
        logger.error(f"Error calculating distribution score: {e}")
        return 0

def calculate_cost_optimization():
    """Calculate cost optimization score."""
    try:
        db = get_db()
        
        # Cost optimization based on bulk purchasing and cost efficiency
        bulk_purchases = db.resources.count_documents({'quantity': {'$gte': 5}})
        total_purchases = db.resources.count_documents({})
        
        bulk_ratio = bulk_purchases / total_purchases if total_purchases > 0 else 0
        
        # Cost variance analysis
        cost_variance_pipeline = [
            {'$group': {
                '_id': '$device_name',
                'avg_cost': {'$avg': '$cost'},
                'min_cost': {'$min': '$cost'},
                'max_cost': {'$max': '$cost'},
                'count': {'$sum': 1}
            }},
            {'$match': {'count': {'$gte': 2}}},
            {'$addFields': {
                'cost_variance': {'$divide': [{'$subtract': ['$max_cost', '$min_cost']}, '$avg_cost']}
            }}
        ]
        
        variances = list(db.resources.aggregate(cost_variance_pipeline))
        avg_variance = sum(v['cost_variance'] for v in variances) / len(variances) if variances else 0
        
        # Optimization score (lower variance and higher bulk ratio = better)
        optimization_score = (bulk_ratio * 50) + max(0, (1 - avg_variance) * 50)
        
        return round(min(100, optimization_score), 2)
        
    except Exception as e:
        logger.error(f"Error calculating cost optimization: {e}")
        return 0

def calculate_maintenance_readiness():
    """Calculate maintenance readiness score."""
    try:
        db = get_db()
        current_date = datetime.time.now()
        
        # Maintenance readiness based on equipment age
        maintenance_pipeline = [
            {'$addFields': {
                'age_years': {'$divide': [{'$subtract': [current_date, '$procurement_date']}, 31557600000]}
            }},
            {'$group': {
                '_id': None,
                'new_equipment': {'$sum': {'$cond': [{'$lt': ['$age_years', 1]}, '$quantity', 0]}},
                'recent_equipment': {'$sum': {'$cond': [{'$and': [{'$gte': ['$age_years', 1]}, {'$lt': ['$age_years', 3]}]}, '$quantity', 0]}},
                'mature_equipment': {'$sum': {'$cond': [{'$and': [{'$gte': ['$age_years', 3]}, {'$lt': ['$age_years', 5]}]}, '$quantity', 0]}},
                'old_equipment': {'$sum': {'$cond': [{'$gte': ['$age_years', 5]}, '$quantity', 0]}},
                'total_equipment': {'$sum': '$quantity'}
            }}
        ]
        
        maintenance_data = list(db.resources.aggregate(maintenance_pipeline))
        
        if not maintenance_data:
            return 0
        
        data = maintenance_data[0]
        total = data['total_equipment']
        
        if total == 0:
            return 0
        
        # Readiness score (newer equipment = higher score)
        readiness_score = (
            (data['new_equipment'] / total * 40) +
            (data['recent_equipment'] / total * 30) +
            (data['mature_equipment'] / total * 20) +
            (data['old_equipment'] / total * 10)
        )
        
        return round(readiness_score, 2)
        
    except Exception as e:
        logger.error(f"Error calculating maintenance readiness: {e}")
        return 0

def calculate_cost_efficiency_score():
    """Calculate overall cost efficiency score."""
    try:
        db = get_db()
        
        # Cost per resource analysis
        efficiency_pipeline = [
            {'$group': {
                '_id': None,
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'total_quantity': {'$sum': '$quantity'},
                'avg_cost': {'$avg': '$cost'}
            }}
        ]
        
        efficiency_data = list(db.resources.aggregate(efficiency_pipeline))
        
        if not efficiency_data:
            return 0
        
        data = efficiency_data[0]
        cost_per_resource = data['total_cost'] / data['total_quantity'] if data['total_quantity'] > 0 else 0
        
        # Normalize to 0-100 scale (lower cost per resource = higher efficiency)
        efficiency_score = max(0, 100 - (cost_per_resource / 1000))
        
        return round(min(100, efficiency_score), 2)
        
    except Exception as e:
        logger.error(f"Error calculating cost efficiency: {e}")
        return 0

def calculate_budget_utilization():
    """Calculate budget utilization rate."""
    try:
        db = get_db()
        
        # Assuming a total budget (this could be configured)
        estimated_total_budget = 100000000  # 10 crores
        
        actual_spending = list(db.resources.aggregate([
            {'$group': {'_id': None, 'total': {'$sum': {'$multiply': ['$cost', '$quantity']}}}}
        ]))
        
        actual_spending = actual_spending[0]['total'] if actual_spending else 0
        
        utilization_rate = (actual_spending / estimated_total_budget) * 100
        
        return round(min(100, utilization_rate), 2)
        
    except Exception as e:
        logger.error(f"Error calculating budget utilization: {e}")
        return 0

def generate_utilization_recommendations(location_density, device_utilization):
    """Generate actionable recommendations based on utilization data."""
    recommendations = []
    
    try:
        # Analyze location density for recommendations
        if location_density:
            high_density_locations = [loc for loc in location_density if loc['resource_count'] > 50]
            low_density_locations = [loc for loc in location_density if loc['resource_count'] < 5]
            
            if high_density_locations:
                recommendations.append({
                    'category': 'Space Optimization',
                    'priority': 'High',
                    'recommendation': f'Consider redistributing resources from high-density locations like {high_density_locations[0]["_id"]} to optimize space utilization.',
                    'impact': 'Improved space efficiency and resource accessibility'
                })
            
            if low_density_locations:
                recommendations.append({
                    'category': 'Resource Allocation',
                    'priority': 'Medium',
                    'recommendation': f'Low-density locations like {low_density_locations[0]["_id"]} could accommodate additional resources.',
                    'impact': 'Better resource distribution across campus'
                })
        
        # Analyze device utilization for recommendations
        if device_utilization:
            underutilized_devices = [dev for dev in device_utilization if dev['location_spread'] < 3]
            popular_devices = [dev for dev in device_utilization if dev['total_quantity'] > 20]
            
            if underutilized_devices:
                recommendations.append({
                    'category': 'Equipment Utilization',
                    'priority': 'Medium',
                    'recommendation': f'Consider broader deployment of {underutilized_devices[0]["_id"]} across more locations.',
                    'impact': 'Increased equipment utilization and accessibility'
                })
            
            if popular_devices:
                recommendations.append({
                    'category': 'Procurement Planning',
                    'priority': 'Low',
                    'recommendation': f'High-demand equipment like {popular_devices[0]["_id"]} may require additional procurement planning.',
                    'impact': 'Proactive resource planning and availability'
                })
        
        # General recommendations
        recommendations.extend([
            {
                'category': 'Maintenance',
                'priority': 'High',
                'recommendation': 'Implement preventive maintenance schedules for equipment older than 3 years.',
                'impact': 'Extended equipment lifespan and reduced downtime'
            },
            {
                'category': 'Cost Optimization',
                'priority': 'Medium',
                'recommendation': 'Consider bulk purchasing agreements for frequently procured items.',
                'impact': 'Reduced per-unit costs and budget optimization'
            }
        ])
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return []

def generate_monthly_cost_trends():
    """Generate monthly cost trends for the last 12 months."""
    try:
        db = get_db()
        
        # Get last 12 months
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        monthly_pipeline = [
            {'$match': {
                'procurement_date': {'$gte': start_date, '$lte': end_date}
            }},
            {'$group': {
                '_id': {
                    'year': {'$year': '$procurement_date'},
                    'month': {'$month': '$procurement_date'}
                },
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'resource_count': {'$sum': '$quantity'}
            }},
            {'$sort': {'_id.year': 1, '_id.month': 1}}
        ]
        
        monthly_data = list(db.resources.aggregate(monthly_pipeline))
        
        # Format for chart consumption
        categories = []
        cost_data = []
        quantity_data = []
        
        for item in monthly_data:
            month_year = f"{calendar.month_abbr[item['_id']['month']]} {item['_id']['year']}"
            categories.append(month_year)
            cost_data.append(item['total_cost'])
            quantity_data.append(item['resource_count'])
        
        return {
            'categories': categories,
            'series': [
                {'name': 'Total Cost', 'data': cost_data, 'type': 'line'},
                {'name': 'Quantity', 'data': quantity_data, 'type': 'line', 'yAxis': 1}
            ],
            'type': 'line'
        }
        
    except Exception as e:
        logger.error(f"Error generating monthly cost trends: {e}")
        return {'categories': [], 'series': [], 'type': 'line'}

def generate_cost_category_donut():
    """Generate cost category breakdown for donut chart."""
    try:
        db = get_db()
        
        # Define cost categories
        cost_categories = [
            {'name': 'High Value (>₹1L)', 'min': 100000, 'max': None},
            {'name': 'Medium Value (₹50K-₹1L)', 'min': 50000, 'max': 100000},
            {'name': 'Low Value (<₹50K)', 'min': 0, 'max': 50000}
        ]
        
        category_data = []
        
        for category in cost_categories:
            filter_condition = {'cost': {'$gte': category['min']}}
            if category['max']:
                filter_condition['cost']['$lt'] = category['max']
            
            total_cost = list(db.resources.aggregate([
                {'$match': filter_condition},
                {'$group': {'_id': None, 'total': {'$sum': {'$multiply': ['$cost', '$quantity']}}}}
            ]))
            
            total_cost = total_cost[0]['total'] if total_cost else 0
            category_data.append({'name': category['name'], 'value': total_cost})
        
        return {
            'series': [item['value'] for item in category_data],
            'labels': [item['name'] for item in category_data],
            'type': 'donut'
        }
        
    except Exception as e:
        logger.error(f"Error generating cost category donut: {e}")
        return {'series': [], 'labels': [], 'type': 'donut'}

def generate_location_distribution_donut():
    """Generate location distribution for donut chart."""
    try:
        db = get_db()
        
        location_pipeline = [
            {'$group': {
                '_id': '$location',
                'resource_count': {'$sum': '$quantity'}
            }},
            {'$sort': {'resource_count': -1}},
            {'$limit': 8}  # Top 8 locations
        ]
        
        location_data = list(db.resources.aggregate(location_pipeline))
        
        return {
            'series': [item['resource_count'] for item in location_data],
            'labels': [item['_id'] for item in location_data],
            'type': 'donut'
        }
        
    except Exception as e:
        logger.error(f"Error generating location distribution donut: {e}")
        return {'series': [], 'labels': [], 'type': 'donut'}

def generate_heatmap_data():
    """Generate heatmap data for resource density visualization."""
    try:
        db = get_db()
        
        heatmap_pipeline = [
            {'$group': {
                '_id': {
                    'department': '$department',
                    'location': '$location'
                },
                'resource_count': {'$sum': '$quantity'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}}
            }},
            {'$sort': {'resource_count': -1}}
        ]
        
        heatmap_data = list(db.resources.aggregate(heatmap_pipeline))
        
        # Format for heatmap visualization
        formatted_data = []
        for item in heatmap_data:
            formatted_data.append({
                'x': item['_id']['department'],
                'y': item['_id']['location'],
                'value': item['resource_count'],
                'cost': item['total_cost']
            })
        
        return {
            'data': formatted_data,
            'type': 'heatmap'
        }
        
    except Exception as e:
        logger.error(f"Error generating heatmap data: {e}")
        return {'data': [], 'type': 'heatmap'}

@dashboard_bp.route('/department-distribution', methods=['GET'])
@require_auth
def get_department_distribution():
    """
    Get department-wise asset distribution for charts.
    """
    try:
        db = get_db()
        
        # Get department distribution by quantity (asset count)
        quantity_pipeline = [
            {'$group': {
                '_id': '$department',
                'asset_count': {'$sum': '$quantity'},
                'resource_entries': {'$sum': 1},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'unique_devices': {'$addToSet': '$device_name'},
                'unique_locations': {'$addToSet': '$location'}
            }},
            {'$sort': {'asset_count': -1}}
        ]
        
        dept_data = list(db.resources.aggregate(quantity_pipeline))
        
        # Format for different chart types
        pie_chart_data = {
            'labels': [item['_id'] for item in dept_data],
            'data': [item['asset_count'] for item in dept_data],
            'total': sum(item['asset_count'] for item in dept_data),
            'type': 'pie'
        }
        
        bar_chart_data = {
            'categories': [item['_id'] for item in dept_data],
            'series': [{
                'name': 'Asset Count',
                'data': [item['asset_count'] for item in dept_data]
            }],
            'type': 'bar'
        }
        
        # Detailed department info
        detailed_data = []
        for item in dept_data:
            detailed_data.append({
                'department': item['_id'],
                'asset_count': item['asset_count'],
                'resource_entries': item['resource_entries'],
                'total_cost': item['total_cost'],
                'unique_devices': len(item['unique_devices']),
                'unique_locations': len(item['unique_locations']),
                'avg_cost_per_asset': item['total_cost'] / item['asset_count'] if item['asset_count'] > 0 else 0
            })
        
        return jsonify({
            'pie_chart': pie_chart_data,
            'bar_chart': bar_chart_data,
            'detailed_data': detailed_data,
            'summary': {
                'total_departments': len(dept_data),
                'total_assets': sum(item['asset_count'] for item in dept_data),
                'total_value': sum(item['total_cost'] for item in dept_data)
            },
            'generated_at': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting department distribution: {e}")
        return jsonify({'error': 'Failed to get department distribution'}), 500

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@dashboard_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors."""
    return jsonify({'error': 'Bad request'}), 400

@dashboard_bp.errorhandler(404)
def not_found(error):
    """Handle not found errors."""
    return jsonify({'error': 'Dashboard data not found'}), 404

@dashboard_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    return jsonify({'error': 'Internal server error'}), 500
