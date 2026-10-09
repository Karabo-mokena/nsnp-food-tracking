from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from projectApp.views import (
    create_delivery_view,
    login_view,
    register_view,
    dashboard_view,
    manager_dashboard_view,
    school_staff_view,
    logout_view,
    report_issue_view,
    reports_view,
    download_report_view,
    notifications_view,
    user_management_view,
    approve_user_view,
    reject_user_view,
    inventory_view,
    edit_inventory_view,
    delete_inventory_view,
    edit_user_view,
    delete_user_view,
    update_issue_status_view,
    update_delivery_status_view,
    profile_view,
    change_password_view,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('driver-dashboard/', dashboard_view, name='driver_dashboard'),
    path('manager-dashboard/', manager_dashboard_view, name='manager_dashboard'),
    path('school-staff/', school_staff_view, name='school_staff'),
    path('logout/', logout_view, name='logout'),
    path('report-issue/', report_issue_view, name='report_issue'),
    path(
        'issues/<int:issue_id>/update-status/',
        update_issue_status_view,
        name='update_issue_status'
    ),
    path('reports/', reports_view, name='reports'),
    path('reports/download/', download_report_view, name='download_report'),
    path('notifications/', notifications_view, name='notification'),
    path('user-management/', user_management_view, name='user_management'),
    path('user-management/edit/<int:user_id>/', edit_user_view, name='edit_user'),
    path('user-management/delete/<int:user_id>/', delete_user_view, name='delete_user'),
    path('inventory/', inventory_view, name='inventory'),
    path('inventory/edit/<int:inventory_id>/', edit_inventory_view, name='edit_inventory'),
    path('inventory/delete/<int:inventory_id>/', delete_inventory_view, name='delete_inventory'),
    path(
        'user-management/approve/<int:user_id>/',
        approve_user_view,
        name='approve_user'
    ),
    path(
        'user-management/reject/<int:user_id>/',
        reject_user_view,
        name='reject_user'
    ),
    path('deliveries/create/', create_delivery_view, name='create_delivery'),
    path(
        'deliveries/<int:delivery_id>/update-status/',
        update_delivery_status_view,
        name='update_delivery_status'
    ),
    path('profile/', profile_view, name='profile'),
    path('profile/change-password/', change_password_view, name='change_password'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)