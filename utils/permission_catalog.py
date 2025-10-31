"""
Smart Permission Catalog with Group-Based ID System
Manages all permissions with intelligent numbering for easy organization
"""

from datetime import datetime

class PermissionCatalog:
    """Smart permission catalog with group-based ID system"""
    
    # Permission Groups with Smart ID Ranges
    PERMISSION_GROUPS = {
        # Group 1: Core User Management (11-199)
        'user_management': {
            'range': (11, 199),
            'resources': ['users', 'roles', 'profiles', 'verifications', 'messaging', 'profile']
        },
        
        # Group 2: Organization Management (21-299)
        'organization_management': {
            'range': (21, 299),
            'resources': ['organizations', 'organization_types']
        },
        
        # Group 3: Business Operations (31-399)
        'business_operations': {
            'range': (31, 399),
            'resources': ['deals', 'deal_requests', 'reviews', 'notifications', 'feedback']
        },
        
        # Group 4: Bank & Content Management (41-499)
        'bank_content': {
            'range': (41, 499),
            'resources': ['banks', 'items', 'item_types', 'needs', 'categories', 'subcategories']
        },
        
        # Group 5: AI & Matching System (51-599)
        'ai_matching': {
            'range': (51, 599),
            'resources': ['ai_matching', 'ai_recommendations']
        },
        
        # Group 6: Scoring System (61-699)
        'scoring_system': {
            'range': (61, 699),
            'resources': ['scoring', 'scoring_management']
        },
        
        # Group 7: Analytics & Reporting (71-799)
        'analytics_reporting': {
            'range': (71, 799),
            'resources': ['analytics', 'reports', 'performance_metrics', 'ab_tests']
        },
        
        # Group 8: System Administration (81-899)
        'system_administration': {
            'range': (81, 899),
            'resources': ['system_settings', 'monitoring', 'security', 'api', 'system_health', 'error_logs', 'system_logs', 'admin', 'dashboard', 'settings', 'logs']
        },
        
        # Group 9: Content Management System (91-999)
        'cms': {
            'range': (91, 999),
            'resources': ['cms', 'pages', 'content_blocks', 'navigation', 'email_templates']
        },
        
        # Group 10: Chatbot System (101-1099)
        'chatbot_system': {
            'range': (101, 1099),
            'resources': ['chatbots', 'chatbot_flows', 'chatbot_questions', 'chatbot_responses', 'step_blocks', 'chatbot']
        },
        
        # Group 11: Data Management (111-1199)
        'data_management': {
            'range': (111, 1199),
            'resources': ['data_collectors', 'data_collection', 'collectors', 'data_mappings', 'integrations']
        },
        
        # Group 12: Dynamic Configuration (121-1299)
        'dynamic_config': {
            'range': (121, 1299),
            'resources': ['dynamic_buttons', 'item_types']
        },
        
        # Group 13: Admin Dashboard (131-1399)
        'admin_dashboard': {
            'range': (131, 1399),
            'resources': ['admin_dashboard', 'admin_management']
        },
        
        # Group 14: Wallet & Financial (141-1499)
        'wallet_financial': {
            'range': (141, 1499),
            'resources': ['wallet', 'wallet_admin', 'earnings', 'withdrawals', 'transactions']
        }
    }
    
    # Complete Permission Catalog with Smart IDs
    PERMISSIONS = {
        # Group 1: User Management (11-199)
        11: {'resource': 'users', 'action': 'view', 'name': 'users.view', 'description': 'View user accounts'},
        12: {'resource': 'users', 'action': 'create', 'name': 'users.create', 'description': 'Create new user accounts'},
        13: {'resource': 'users', 'action': 'edit', 'name': 'users.edit', 'description': 'Edit user accounts'},
        14: {'resource': 'users', 'action': 'delete', 'name': 'users.delete', 'description': 'Delete user accounts'},
        15: {'resource': 'users', 'action': 'manage_roles', 'name': 'users.manage_roles', 'description': 'Manage user role assignments'},
        16: {'resource': 'users', 'action': 'toggle_status', 'name': 'users.toggle_status', 'description': 'Activate/deactivate user accounts'},
        17: {'resource': 'users', 'action': 'verify_email', 'name': 'users.verify_email', 'description': 'Verify user email addresses'},
        18: {'resource': 'users', 'action': 'assign_roles', 'name': 'users.assign_roles', 'description': 'Assign roles to users'},
        
        21: {'resource': 'roles', 'action': 'view', 'name': 'roles.view', 'description': 'View role definitions'},
        22: {'resource': 'roles', 'action': 'create', 'name': 'roles.create', 'description': 'Create new roles'},
        23: {'resource': 'roles', 'action': 'edit', 'name': 'roles.edit', 'description': 'Edit role definitions'},
        24: {'resource': 'roles', 'action': 'delete', 'name': 'roles.delete', 'description': 'Delete roles'},
        25: {'resource': 'roles', 'action': 'manage_permissions', 'name': 'roles.manage_permissions', 'description': 'Manage role permissions'},
        
        31: {'resource': 'profiles', 'action': 'view_own', 'name': 'profiles.view_own', 'description': 'View own profile'},
        32: {'resource': 'profiles', 'action': 'create', 'name': 'profiles.create', 'description': 'Create new profile'},
        33: {'resource': 'profiles', 'action': 'edit_own', 'name': 'profiles.edit_own', 'description': 'Edit own profile'},
        34: {'resource': 'profiles', 'action': 'delete', 'name': 'profiles.delete', 'description': 'Delete profile'},
        35: {'resource': 'profiles', 'action': 'view_other', 'name': 'profiles.view_other', 'description': 'View other user profiles'},
        36: {'resource': 'profiles', 'action': 'edit_other', 'name': 'profiles.edit_other', 'description': 'Edit other user profiles'},
        37: {'resource': 'profiles', 'action': 'view_private', 'name': 'profiles.view_private', 'description': 'View private profile information'},
        38: {'resource': 'profiles', 'action': 'view_about_own', 'name': 'profiles.view_about_own', 'description': 'View own profile about section'},
        39: {'resource': 'profiles', 'action': 'view_about_others', 'name': 'profiles.view_about_others', 'description': 'View others profile about section'},
        40: {'resource': 'profiles', 'action': 'view_activity_own', 'name': 'profiles.view_activity_own', 'description': 'View own profile activity'},
        41: {'resource': 'profiles', 'action': 'view_activity_others', 'name': 'profiles.view_activity_others', 'description': 'View others profile activity'},
        
        51: {'resource': 'verifications', 'action': 'approve', 'name': 'verifications.approve', 'description': 'Approve verification requests'},
        52: {'resource': 'verifications', 'action': 'reject', 'name': 'verifications.reject', 'description': 'Reject verification requests'},
        53: {'resource': 'verifications', 'action': 'manage', 'name': 'verifications.manage', 'description': 'Manage verification system'},
        
        54: {'resource': 'messaging', 'action': 'send', 'name': 'messaging.send', 'description': 'Send messages to users'},
        55: {'resource': 'messaging', 'action': 'view_own', 'name': 'messaging.view_own', 'description': 'View own messages'},
        
        # Group 2: Organization Management (21-299)
        121: {'resource': 'organizations', 'action': 'view', 'name': 'organizations.view', 'description': 'View organizations'},
        122: {'resource': 'organizations', 'action': 'create', 'name': 'organizations.create', 'description': 'Create new organizations'},
        123: {'resource': 'organizations', 'action': 'edit', 'name': 'organizations.edit', 'description': 'Edit organizations'},
        124: {'resource': 'organizations', 'action': 'delete', 'name': 'organizations.delete', 'description': 'Delete organizations'},
        125: {'resource': 'organizations', 'action': 'join', 'name': 'organizations.join', 'description': 'Join organizations'},
        126: {'resource': 'organizations', 'action': 'manage_members', 'name': 'organizations.manage_members', 'description': 'Manage organization members'},
        127: {'resource': 'organizations', 'action': 'verify', 'name': 'organizations.verify', 'description': 'Verify organizations'},
        128: {'resource': 'organizations', 'action': 'view_private', 'name': 'organizations.view_private', 'description': 'View private organization data'},
        129: {'resource': 'organizations', 'action': 'view_about_own', 'name': 'organizations.view_about_own', 'description': 'View own organization about'},
        130: {'resource': 'organizations', 'action': 'view_about_others', 'name': 'organizations.view_about_others', 'description': 'View other organizations about'},
        131: {'resource': 'organizations', 'action': 'view_members_own', 'name': 'organizations.view_members_own', 'description': 'View own organization members'},
        132: {'resource': 'organizations', 'action': 'view_members_others', 'name': 'organizations.view_members_others', 'description': 'View other organizations members'},
        133: {'resource': 'organizations', 'action': 'view_activity_own', 'name': 'organizations.view_activity_own', 'description': 'View own organization activity'},
        134: {'resource': 'organizations', 'action': 'view_activity_others', 'name': 'organizations.view_activity_others', 'description': 'View other organizations activity'},
        
        141: {'resource': 'organization_types', 'action': 'create', 'name': 'organization_types.create', 'description': 'Create organization types'},
        142: {'resource': 'organization_types', 'action': 'delete', 'name': 'organization_types.delete', 'description': 'Delete organization types'},
        
        # Group 3: Business Operations (31-399)
        221: {'resource': 'deals', 'action': 'view', 'name': 'deals.view', 'description': 'View deals'},
        222: {'resource': 'deals', 'action': 'create', 'name': 'deals.create', 'description': 'Create new deals'},
        223: {'resource': 'deals', 'action': 'edit', 'name': 'deals.edit', 'description': 'Edit deals'},
        224: {'resource': 'deals', 'action': 'delete', 'name': 'deals.delete', 'description': 'Delete deals'},
        225: {'resource': 'deals', 'action': 'manage_status', 'name': 'deals.manage_status', 'description': 'Manage deal status'},
        226: {'resource': 'deals', 'action': 'send_messages', 'name': 'deals.send_messages', 'description': 'Send deal messages'},
        
        231: {'resource': 'deal_requests', 'action': 'create', 'name': 'deal_requests.create', 'description': 'Create deal requests'},
        232: {'resource': 'deal_requests', 'action': 'view_own', 'name': 'deal_requests.view_own', 'description': 'View own deal requests'},
        233: {'resource': 'deal_requests', 'action': 'view_all', 'name': 'deal_requests.view_all', 'description': 'View all deal requests'},
        234: {'resource': 'deal_requests', 'action': 'edit_own', 'name': 'deal_requests.edit_own', 'description': 'Edit own deal requests'},
        235: {'resource': 'deal_requests', 'action': 'delete_own', 'name': 'deal_requests.delete_own', 'description': 'Delete own deal requests'},
        236: {'resource': 'deal_requests', 'action': 'take_request', 'name': 'deal_requests.take_request', 'description': 'Take deal requests'},
        237: {'resource': 'deal_requests', 'action': 'assign_request', 'name': 'deal_requests.assign_request', 'description': 'Assign deal requests'},
        238: {'resource': 'deal_requests', 'action': 'add_update', 'name': 'deal_requests.add_update', 'description': 'Add updates to deal requests'},
        239: {'resource': 'deal_requests', 'action': 'manage_status', 'name': 'deal_requests.manage_status', 'description': 'Manage deal request status'},
        240: {'resource': 'deal_requests', 'action': 'view_updates', 'name': 'deal_requests.view_updates', 'description': 'View deal request updates'},
        
        251: {'resource': 'reviews', 'action': 'create', 'name': 'reviews.create', 'description': 'Create reviews'},
        252: {'resource': 'reviews', 'action': 'edit_own', 'name': 'reviews.edit_own', 'description': 'Edit own reviews'},
        253: {'resource': 'reviews', 'action': 'view', 'name': 'reviews.view', 'description': 'View reviews'},
        254: {'resource': 'reviews', 'action': 'view_hidden', 'name': 'reviews.view_hidden', 'description': 'View hidden reviews (admin/moderation)'},
        255: {'resource': 'reviews', 'action': 'edit', 'name': 'reviews.edit', 'description': 'Edit any review (admin)'},
        256: {'resource': 'reviews', 'action': 'delete', 'name': 'reviews.delete', 'description': 'Delete reviews (admin)'},
        257: {'resource': 'reviews', 'action': 'manage', 'name': 'reviews.manage', 'description': 'Manage reviews in admin panel'},
        
        261: {'resource': 'notifications', 'action': 'create', 'name': 'notifications.create', 'description': 'Create notifications'},
        262: {'resource': 'notifications', 'action': 'delete', 'name': 'notifications.delete', 'description': 'Delete notifications'},
        263: {'resource': 'notifications', 'action': 'send', 'name': 'notifications.send', 'description': 'Send notifications'},
        
        271: {'resource': 'feedback', 'action': 'manage', 'name': 'feedback.manage', 'description': 'Manage feedback'},
        272: {'resource': 'feedback', 'action': 'respond', 'name': 'feedback.respond', 'description': 'Respond to feedback'},
        
        # Group 4: Bank & Content Management (41-499)
        321: {'resource': 'banks', 'action': 'view', 'name': 'banks.view', 'description': 'View banks'},
        322: {'resource': 'banks', 'action': 'create', 'name': 'banks.create', 'description': 'Create new banks'},
        323: {'resource': 'banks', 'action': 'edit', 'name': 'banks.edit', 'description': 'Edit banks'},
        324: {'resource': 'banks', 'action': 'delete', 'name': 'banks.delete', 'description': 'Delete banks'},
        325: {'resource': 'banks', 'action': 'manage_content', 'name': 'banks.manage_content', 'description': 'Manage bank content'},
        326: {'resource': 'banks', 'action': 'use', 'name': 'banks.use', 'description': 'Use bank services'},
        
        331: {'resource': 'items', 'action': 'view', 'name': 'items.view', 'description': 'View items'},
        332: {'resource': 'items', 'action': 'create', 'name': 'items.create', 'description': 'Create new items'},
        333: {'resource': 'items', 'action': 'edit', 'name': 'items.edit', 'description': 'Edit items'},
        334: {'resource': 'items', 'action': 'delete', 'name': 'items.delete', 'description': 'Delete items'},
        335: {'resource': 'items', 'action': 'verify', 'name': 'items.verify', 'description': 'Verify items'},
        336: {'resource': 'items', 'action': 'manage_categories', 'name': 'items.manage_categories', 'description': 'Manage item categories'},
        
        341: {'resource': 'needs', 'action': 'create', 'name': 'needs.create', 'description': 'Create needs'},
        342: {'resource': 'needs', 'action': 'delete', 'name': 'needs.delete', 'description': 'Delete needs'},
        343: {'resource': 'needs', 'action': 'verify', 'name': 'needs.verify', 'description': 'Verify needs'},
        
        351: {'resource': 'categories', 'action': 'create', 'name': 'categories.create', 'description': 'Create categories'},
        352: {'resource': 'categories', 'action': 'delete', 'name': 'categories.delete', 'description': 'Delete categories'},
        353: {'resource': 'categories', 'action': 'subcategories', 'name': 'categories.subcategories', 'description': 'Manage subcategories'},
        
        361: {'resource': 'subcategories', 'action': 'create', 'name': 'subcategories.create', 'description': 'Create subcategories'},
        362: {'resource': 'subcategories', 'action': 'delete', 'name': 'subcategories.delete', 'description': 'Delete subcategories'},
        
        371: {'resource': 'item_types', 'action': 'create', 'name': 'item_types.create', 'description': 'Create item types'},
        372: {'resource': 'item_types', 'action': 'delete', 'name': 'item_types.delete', 'description': 'Delete item types'},
        
        # Group 5: AI & Matching System (51-599)
        421: {'resource': 'ai_matching', 'action': 'access_dashboard', 'name': 'ai_matching.access_dashboard', 'description': 'Access AI matching dashboard'},
        422: {'resource': 'ai_matching', 'action': 'access_engine', 'name': 'ai_matching.access_engine', 'description': 'Access AI matching engine'},
        423: {'resource': 'ai_matching', 'action': 'generate_recommendations', 'name': 'ai_matching.generate_recommendations', 'description': 'Generate AI recommendations'},
        424: {'resource': 'ai_matching', 'action': 'manage_matches', 'name': 'ai_matching.manage_matches', 'description': 'Manage AI matches'},
        
        431: {'resource': 'ai_recommendations', 'action': 'create', 'name': 'ai_recommendations.create', 'description': 'Create AI recommendations'},
        432: {'resource': 'ai_recommendations', 'action': 'delete', 'name': 'ai_recommendations.delete', 'description': 'Delete AI recommendations'},
        433: {'resource': 'ai_recommendations', 'action': 'rate', 'name': 'ai_recommendations.rate', 'description': 'Rate AI recommendations'},
        434: {'resource': 'ai_recommendations', 'action': 'view_reports', 'name': 'ai_recommendations.view_reports', 'description': 'View AI recommendation reports'},
        
        # Group 6: Scoring System (61-699)
        521: {'resource': 'scoring', 'action': 'manage', 'name': 'scoring.manage', 'description': 'Manage scoring system'},
        522: {'resource': 'scoring', 'action': 'visibility', 'name': 'scoring.visibility', 'description': 'Manage visibility scores'},
        523: {'resource': 'scoring', 'action': 'credibility', 'name': 'scoring.credibility', 'description': 'Manage credibility scores'},
        524: {'resource': 'scoring', 'action': 'review', 'name': 'scoring.review', 'description': 'Review scores'},
        525: {'resource': 'scoring', 'action': 'recalculate', 'name': 'scoring.recalculate', 'description': 'Recalculate scores'},
        
        531: {'resource': 'scoring_management', 'action': 'access', 'name': 'scoring_management.access', 'description': 'Access scoring management'},
        532: {'resource': 'scoring_management', 'action': 'visibility', 'name': 'scoring_management.visibility', 'description': 'Manage visibility in scoring'},
        533: {'resource': 'scoring_management', 'action': 'credibility', 'name': 'scoring_management.credibility', 'description': 'Manage credibility in scoring'},
        534: {'resource': 'scoring_management', 'action': 'review', 'name': 'scoring_management.review', 'description': 'Review scoring management'},
        
        # Group 7: Analytics & Reporting (71-799)
        621: {'resource': 'analytics', 'action': 'view', 'name': 'analytics.view', 'description': 'View analytics'},
        622: {'resource': 'analytics', 'action': 'use', 'name': 'analytics.use', 'description': 'Use analytics'},
        623: {'resource': 'analytics', 'action': 'advanced_analytics', 'name': 'analytics.advanced_analytics', 'description': 'Access advanced analytics'},
        624: {'resource': 'analytics', 'action': 'realtime_analytics', 'name': 'analytics.realtime_analytics', 'description': 'Access realtime analytics'},
        625: {'resource': 'analytics', 'action': 'ab_testing', 'name': 'analytics.ab_testing', 'description': 'Access A/B testing'},
        626: {'resource': 'analytics', 'action': 'events', 'name': 'analytics.events', 'description': 'Access event analytics'},
        
        631: {'resource': 'reports', 'action': 'generate', 'name': 'reports.generate', 'description': 'Generate reports'},
        632: {'resource': 'reports', 'action': 'view_all', 'name': 'reports.view_all', 'description': 'View all reports'},
        633: {'resource': 'reports', 'action': 'export', 'name': 'reports.export', 'description': 'Export reports'},
        634: {'resource': 'reports', 'action': 'comprehensive', 'name': 'reports.comprehensive', 'description': 'Access comprehensive reports'},
        635: {'resource': 'reports', 'action': 'overview', 'name': 'reports.overview', 'description': 'Access overview reports'},
        636: {'resource': 'reports', 'action': 'user_activity', 'name': 'reports.user_activity', 'description': 'Access user activity reports'},
        637: {'resource': 'reports', 'action': 'system_performance', 'name': 'reports.system_performance', 'description': 'Access system performance reports'},
        638: {'resource': 'reports', 'action': 'business_metrics', 'name': 'reports.business_metrics', 'description': 'Access business metrics reports'},
        639: {'resource': 'reports', 'action': 'security_events', 'name': 'reports.security_events', 'description': 'Access security events reports'},
        640: {'resource': 'reports', 'action': 'ab_test_results', 'name': 'reports.ab_test_results', 'description': 'Access A/B test results reports'},
        
        651: {'resource': 'performance_metrics', 'action': 'monitor', 'name': 'performance_metrics.monitor', 'description': 'Monitor performance metrics'},
        
        661: {'resource': 'ab_tests', 'action': 'create', 'name': 'ab_tests.create', 'description': 'Create A/B tests'},
        662: {'resource': 'ab_tests', 'action': 'delete', 'name': 'ab_tests.delete', 'description': 'Delete A/B tests'},
        663: {'resource': 'ab_tests', 'action': 'run', 'name': 'ab_tests.run', 'description': 'Run A/B tests'},
        
        # Group 8: System Administration (81-899)
        721: {'resource': 'system_settings', 'action': 'view', 'name': 'system_settings.view', 'description': 'View system settings'},
        722: {'resource': 'system_settings', 'action': 'edit', 'name': 'system_settings.edit', 'description': 'Edit system settings'},
        
        731: {'resource': 'monitoring', 'action': 'system_health', 'name': 'monitoring.system_health', 'description': 'Monitor system health'},
        732: {'resource': 'monitoring', 'action': 'performance', 'name': 'monitoring.performance', 'description': 'Monitor system performance'},
        733: {'resource': 'monitoring', 'action': 'errors', 'name': 'monitoring.errors', 'description': 'Monitor system errors'},
        
        741: {'resource': 'security', 'action': 'monitor', 'name': 'security.monitor', 'description': 'Monitor security'},
        742: {'resource': 'security', 'action': 'manage_incidents', 'name': 'security.manage_incidents', 'description': 'Manage security incidents'},
        743: {'resource': 'security', 'action': 'audit_logs', 'name': 'security.audit_logs', 'description': 'Access security audit logs'},
        
        751: {'resource': 'api', 'action': 'access', 'name': 'api.access', 'description': 'Access API'},
        752: {'resource': 'api', 'action': 'manage_keys', 'name': 'api.manage_keys', 'description': 'Manage API keys'},
        753: {'resource': 'api', 'action': 'monitor_usage', 'name': 'api.monitor_usage', 'description': 'Monitor API usage'},
        
        761: {'resource': 'system_health', 'action': 'monitor', 'name': 'system_health.monitor', 'description': 'Monitor system health'},
        762: {'resource': 'system_health', 'action': 'detailed', 'name': 'system_health.detailed', 'description': 'Access detailed system health'},
        
        771: {'resource': 'error_logs', 'action': 'manage', 'name': 'error_logs.manage', 'description': 'Manage error logs'},
        
        781: {'resource': 'system_logs', 'action': 'monitor', 'name': 'system_logs.monitor', 'description': 'Monitor system logs'},
        
        791: {'resource': 'dashboard', 'action': 'view', 'name': 'dashboard.view', 'description': 'View dashboard'},
        
        801: {'resource': 'admin', 'action': 'access', 'name': 'admin.access', 'description': 'Access admin panel'},
        
        811: {'resource': 'logs', 'action': 'view', 'name': 'logs.view', 'description': 'View logs'},
        
        821: {'resource': 'settings', 'action': 'manage', 'name': 'settings.manage', 'description': 'Manage settings'},
        
        # Group 9: Content Management System (91-999)
        921: {'resource': 'cms', 'action': 'create', 'name': 'cms.create', 'description': 'Create CMS content'},
        922: {'resource': 'cms', 'action': 'delete', 'name': 'cms.delete', 'description': 'Delete CMS content'},
        923: {'resource': 'cms', 'action': 'manage_pages', 'name': 'cms.manage_pages', 'description': 'Manage CMS pages'},
        924: {'resource': 'cms', 'action': 'manage_blocks', 'name': 'cms.manage_blocks', 'description': 'Manage CMS blocks'},
        925: {'resource': 'cms', 'action': 'manage_navigation', 'name': 'cms.manage_navigation', 'description': 'Manage CMS navigation'},
        926: {'resource': 'cms', 'action': 'dashboard', 'name': 'cms.dashboard', 'description': 'Access CMS dashboard'},
        
        931: {'resource': 'pages', 'action': 'create', 'name': 'pages.create', 'description': 'Create pages'},
        932: {'resource': 'pages', 'action': 'delete', 'name': 'pages.delete', 'description': 'Delete pages'},
        933: {'resource': 'pages', 'action': 'publish', 'name': 'pages.publish', 'description': 'Publish pages'},
        934: {'resource': 'pages', 'action': 'preview', 'name': 'pages.preview', 'description': 'Preview pages'},
        935: {'resource': 'pages', 'action': 'toggle', 'name': 'pages.toggle', 'description': 'Toggle page status'},
        936: {'resource': 'pages', 'action': 'builder', 'name': 'pages.builder', 'description': 'Use page builder'},
        937: {'resource': 'pages', 'action': 'widgets', 'name': 'pages.widgets', 'description': 'Manage page widgets'},
        
        941: {'resource': 'content_blocks', 'action': 'create', 'name': 'content_blocks.create', 'description': 'Create content blocks'},
        942: {'resource': 'content_blocks', 'action': 'delete', 'name': 'content_blocks.delete', 'description': 'Delete content blocks'},
        943: {'resource': 'content_blocks', 'action': 'toggle', 'name': 'content_blocks.toggle', 'description': 'Toggle content blocks'},
        
        951: {'resource': 'navigation', 'action': 'create', 'name': 'navigation.create', 'description': 'Create navigation'},
        952: {'resource': 'navigation', 'action': 'delete', 'name': 'navigation.delete', 'description': 'Delete navigation'},
        953: {'resource': 'navigation', 'action': 'toggle', 'name': 'navigation.toggle', 'description': 'Toggle navigation'},
        
        961: {'resource': 'email_templates', 'action': 'create', 'name': 'email_templates.create', 'description': 'Create email templates'},
        962: {'resource': 'email_templates', 'action': 'delete', 'name': 'email_templates.delete', 'description': 'Delete email templates'},
        
        # Group 10: Chatbot System (101-1099)
        1021: {'resource': 'chatbots', 'action': 'create', 'name': 'chatbots.create', 'description': 'Create chatbots'},
        1022: {'resource': 'chatbots', 'action': 'delete', 'name': 'chatbots.delete', 'description': 'Delete chatbots'},
        1023: {'resource': 'chatbots', 'action': 'manage_flows', 'name': 'chatbots.manage_flows', 'description': 'Manage chatbot flows'},
        1024: {'resource': 'chatbots', 'action': 'manage_questions', 'name': 'chatbots.manage_questions', 'description': 'Manage chatbot questions'},
        1025: {'resource': 'chatbots', 'action': 'manage_responses', 'name': 'chatbots.manage_responses', 'description': 'Manage chatbot responses'},
        1026: {'resource': 'chatbots', 'action': 'view', 'name': 'chatbots.view', 'description': 'View chatbots'},
        1027: {'resource': 'chatbots', 'action': 'edit', 'name': 'chatbots.edit', 'description': 'Edit chatbots'},
        
        1031: {'resource': 'chatbot_flows', 'action': 'create', 'name': 'chatbot_flows.create', 'description': 'Create chatbot flows'},
        1032: {'resource': 'chatbot_flows', 'action': 'delete', 'name': 'chatbot_flows.delete', 'description': 'Delete chatbot flows'},
        1033: {'resource': 'chatbot_flows', 'action': 'duplicate', 'name': 'chatbot_flows.duplicate', 'description': 'Duplicate chatbot flows'},
        1034: {'resource': 'chatbot_flows', 'action': 'toggle', 'name': 'chatbot_flows.toggle', 'description': 'Toggle chatbot flows'},
        1035: {'resource': 'chatbot_flows', 'action': 'responses', 'name': 'chatbot_flows.responses', 'description': 'Manage chatbot flow responses'},
        1036: {'resource': 'chatbot_flows', 'action': 'analytics', 'name': 'chatbot_flows.analytics', 'description': 'Access chatbot flow analytics'},
        
        1041: {'resource': 'chatbot_questions', 'action': 'create', 'name': 'chatbot_questions.create', 'description': 'Create chatbot questions'},
        1042: {'resource': 'chatbot_questions', 'action': 'delete', 'name': 'chatbot_questions.delete', 'description': 'Delete chatbot questions'},
        
        1051: {'resource': 'chatbot_responses', 'action': 'create', 'name': 'chatbot_responses.create', 'description': 'Create chatbot responses'},
        1052: {'resource': 'chatbot_responses', 'action': 'delete', 'name': 'chatbot_responses.delete', 'description': 'Delete chatbot responses'},
        
        1061: {'resource': 'step_blocks', 'action': 'create', 'name': 'step_blocks.create', 'description': 'Create step blocks'},
        1062: {'resource': 'step_blocks', 'action': 'delete', 'name': 'step_blocks.delete', 'description': 'Delete step blocks'},
        1063: {'resource': 'step_blocks', 'action': 'questions', 'name': 'step_blocks.questions', 'description': 'Manage step block questions'},
        
        1071: {'resource': 'chatbot', 'action': 'use', 'name': 'chatbot.use', 'description': 'Use chatbot'},
        
        # Group 11: Data Management (111-1199)
        1121: {'resource': 'data_collectors', 'action': 'create', 'name': 'data_collectors.create', 'description': 'Create data collectors'},
        1122: {'resource': 'data_collectors', 'action': 'delete', 'name': 'data_collectors.delete', 'description': 'Delete data collectors'},
        1123: {'resource': 'data_collectors', 'action': 'run', 'name': 'data_collectors.run', 'description': 'Run data collectors'},
        1124: {'resource': 'data_collectors', 'action': 'monitor', 'name': 'data_collectors.monitor', 'description': 'Monitor data collectors'},
        1125: {'resource': 'data_collectors', 'action': 'test', 'name': 'data_collectors.test', 'description': 'Test data collectors'},
        1126: {'resource': 'data_collectors', 'action': 'toggle', 'name': 'data_collectors.toggle', 'description': 'Toggle data collectors'},
        1127: {'resource': 'data_collectors', 'action': 'logs', 'name': 'data_collectors.logs', 'description': 'Access data collector logs'},
        1128: {'resource': 'data_collectors', 'action': 'data', 'name': 'data_collectors.data', 'description': 'Access data collector data'},
        
        1131: {'resource': 'data_collection', 'action': 'create', 'name': 'data_collection.create', 'description': 'Create data collection'},
        1132: {'resource': 'data_collection', 'action': 'delete', 'name': 'data_collection.delete', 'description': 'Delete data collection'},
        1133: {'resource': 'data_collection', 'action': 'manage', 'name': 'data_collection.manage', 'description': 'Manage data collection'},
        
        1141: {'resource': 'collectors', 'action': 'create', 'name': 'collectors.create', 'description': 'Create collectors'},
        1142: {'resource': 'collectors', 'action': 'delete', 'name': 'collectors.delete', 'description': 'Delete collectors'},
        1143: {'resource': 'collectors', 'action': 'run', 'name': 'collectors.run', 'description': 'Run collectors'},
        1144: {'resource': 'collectors', 'action': 'view', 'name': 'collectors.view', 'description': 'View collectors'},
        1145: {'resource': 'collectors', 'action': 'edit', 'name': 'collectors.edit', 'description': 'Edit collectors'},
        
        1151: {'resource': 'data_mappings', 'action': 'create', 'name': 'data_mappings.create', 'description': 'Create data mappings'},
        1152: {'resource': 'data_mappings', 'action': 'delete', 'name': 'data_mappings.delete', 'description': 'Delete data mappings'},
        
        1161: {'resource': 'integrations', 'action': 'create', 'name': 'integrations.create', 'description': 'Create integrations'},
        1162: {'resource': 'integrations', 'action': 'delete', 'name': 'integrations.delete', 'description': 'Delete integrations'},
        1163: {'resource': 'integrations', 'action': 'test', 'name': 'integrations.test', 'description': 'Test integrations'},
        
        # Group 12: Dynamic Configuration (121-1299)
        1221: {'resource': 'dynamic_buttons', 'action': 'create', 'name': 'dynamic_buttons.create', 'description': 'Create dynamic buttons'},
        1222: {'resource': 'dynamic_buttons', 'action': 'delete', 'name': 'dynamic_buttons.delete', 'description': 'Delete dynamic buttons'},
        
        # Group 13: Admin Dashboard (131-1399)
        1321: {'resource': 'admin_dashboard', 'action': 'access', 'name': 'admin_dashboard.access', 'description': 'Access admin dashboard'},
        1322: {'resource': 'admin_dashboard', 'action': 'view_stats', 'name': 'admin_dashboard.view_stats', 'description': 'View admin dashboard stats'},
        1323: {'resource': 'admin_dashboard', 'action': 'manage_stats', 'name': 'admin_dashboard.manage_stats', 'description': 'Manage admin dashboard stats'},
        
        1331: {'resource': 'admin_management', 'action': 'access', 'name': 'admin_management.access', 'description': 'Access admin management'},
        1332: {'resource': 'admin_management', 'action': 'users', 'name': 'admin_management.users', 'description': 'Manage users in admin'},
        1333: {'resource': 'admin_management', 'action': 'roles', 'name': 'admin_management.roles', 'description': 'Manage roles in admin'},
        1334: {'resource': 'admin_management', 'action': 'deals', 'name': 'admin_management.deals', 'description': 'Manage deals in admin'},
        1335: {'resource': 'admin_management', 'action': 'verifications', 'name': 'admin_management.verifications', 'description': 'Manage verifications in admin'},
        
        # Group 14: Wallet & Financial (141-1499)
        1421: {'resource': 'wallet', 'action': 'view', 'name': 'wallet.view', 'description': 'View wallet'},
        1422: {'resource': 'wallet', 'action': 'manage', 'name': 'wallet.manage', 'description': 'Manage wallet'},
        1423: {'resource': 'wallet', 'action': 'withdraw', 'name': 'wallet.withdraw', 'description': 'Withdraw from wallet'},
        1424: {'resource': 'wallet', 'action': 'view_transactions', 'name': 'wallet.view_transactions', 'description': 'View wallet transactions'},
        
        1431: {'resource': 'wallet_admin', 'action': 'view_all', 'name': 'wallet_admin.view_all', 'description': 'View all wallets'},
        1432: {'resource': 'wallet_admin', 'action': 'manage_all', 'name': 'wallet_admin.manage_all', 'description': 'Manage all wallets'},
        1433: {'resource': 'wallet_admin', 'action': 'process_withdrawals', 'name': 'wallet_admin.process_withdrawals', 'description': 'Process withdrawals'},
        1434: {'resource': 'wallet_admin', 'action': 'view_analytics', 'name': 'wallet_admin.view_analytics', 'description': 'View wallet analytics'},
        
        1441: {'resource': 'earnings', 'action': 'view', 'name': 'earnings.view', 'description': 'View earnings'},
        1442: {'resource': 'earnings', 'action': 'sync', 'name': 'earnings.sync', 'description': 'Sync earnings'},
        1443: {'resource': 'earnings', 'action': 'manage', 'name': 'earnings.manage', 'description': 'Manage earnings'},
        
        1451: {'resource': 'withdrawals', 'action': 'request', 'name': 'withdrawals.request', 'description': 'Request withdrawals'},
        1452: {'resource': 'withdrawals', 'action': 'cancel', 'name': 'withdrawals.cancel', 'description': 'Cancel withdrawals'},
        1453: {'resource': 'withdrawals', 'action': 'view_own', 'name': 'withdrawals.view_own', 'description': 'View own withdrawals'},
        
        1461: {'resource': 'transactions', 'action': 'view_own', 'name': 'transactions.view_own', 'description': 'View own transactions'},
        1462: {'resource': 'transactions', 'action': 'view_all', 'name': 'transactions.view_all', 'description': 'View all transactions'},
    }
    
    @classmethod
    def get_permission_by_id(cls, permission_id):
        """Get permission details by ID"""
        return cls.PERMISSIONS.get(permission_id)
    
    @classmethod
    def get_permission_by_name(cls, permission_name):
        """Get permission ID by name (e.g., 'users.view')"""
        for pid, pdata in cls.PERMISSIONS.items():
            if pdata['name'] == permission_name:
                return pid, pdata
        return None, None
    
    @classmethod
    def get_permissions_by_resource(cls, resource):
        """Get all permissions for a specific resource"""
        permissions = []
        for pid, pdata in cls.PERMISSIONS.items():
            if pdata['resource'] == resource:
                permissions.append((pid, pdata))
        return permissions
    
    @classmethod
    def get_permissions_by_group(cls, group_name):
        """Get all permissions for a specific group"""
        if group_name not in cls.PERMISSION_GROUPS:
            return []
        
        group_range = cls.PERMISSION_GROUPS[group_name]['range']
        permissions = []
        
        for pid, pdata in cls.PERMISSIONS.items():
            if group_range[0] <= pid <= group_range[1]:
                permissions.append((pid, pdata))
        
        return permissions
    
    @classmethod
    def get_all_permissions(cls):
        """Get all permissions"""
        return cls.PERMISSIONS
    
    @classmethod
    def get_permission_groups(cls):
        """Get all permission groups"""
        return cls.PERMISSION_GROUPS
    
    @classmethod
    def get_permission_group_by_id(cls, permission_id):
        """Get the group name that a permission ID belongs to"""
        for group_name, group_info in cls.PERMISSION_GROUPS.items():
            group_range = group_info['range']
            if group_range[0] <= permission_id <= group_range[1]:
                return group_name
        return 'unknown'
    
    @classmethod
    def validate_permission_id(cls, permission_id):
        """Validate if permission ID exists"""
        return permission_id in cls.PERMISSIONS
    
    @classmethod
    def get_next_permission_id(cls, group_name):
        """Get next available permission ID for a group"""
        if group_name not in cls.PERMISSION_GROUPS:
            return None
        
        group_range = cls.PERMISSION_GROUPS[group_name]['range']
        used_ids = [pid for pid in cls.PERMISSIONS.keys() if group_range[0] <= pid <= group_range[1]]
        
        if not used_ids:
            return group_range[0]
        
        max_id = max(used_ids)
        next_id = max_id + 1
        
        if next_id <= group_range[1]:
            return next_id
        
        return None  # Group is full
    
    @classmethod
    def add_custom_permission(cls, group_name, resource, action, description):
        """Add a custom permission to the catalog"""
        permission_id = cls.get_next_permission_id(group_name)
        if not permission_id:
            raise ValueError(f"Group {group_name} is full")
        
        permission_name = f"{resource}.{action}"
        cls.PERMISSIONS[permission_id] = {
            'resource': resource,
            'action': action,
            'name': permission_name,
            'description': description
        }
        
        return permission_id

