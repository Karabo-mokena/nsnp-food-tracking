from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta
from datetime import datetime
import csv
import threading 
from io import BytesIO

from .models import UserProfile, Delivery, Issue, Notification, Inventory


def get_logged_in_user(request):

    user_id = request.session.get('user_id')

    if not user_id:
        return None

    try:
        user = UserProfile.objects.get(id=user_id)

    except UserProfile.DoesNotExist:
        return None

    if user.status != 'Approved':
        return None

    return user

def check_and_alert_low_stock(inventory_item, school_name):

    if inventory_item.quantity < inventory_item.minimum_stock:

        managers = UserProfile.objects.filter(
            role__in=['programme_manager', 'manager'],
            status='Approved'
        )

        shortfall = inventory_item.minimum_stock - inventory_item.quantity

        for manager in managers:

            already_alerted = Notification.objects.filter(
                user=manager,
                notification_type='alert',
                message__contains=f'{inventory_item.food_item} at {school_name}'
            ).filter(
                created_at__date=timezone.localdate()
            ).exists()

            if not already_alerted:

                Notification.objects.create(
                    user=manager,
                    message=f'Low stock alert: {inventory_item.food_item} at {school_name} is at {inventory_item.quantity} units (minimum: {inventory_item.minimum_stock}, short by {shortfall}).',
                    notification_type='alert'
                )
def send_email_async(subject, message, from_email, recipient_list):

    def _send():

        try:

            send_mail(
                subject,
                message,
                from_email,
                recipient_list,
                fail_silently=True,
            )

        except Exception:

            pass

    thread = threading.Thread(target=_send)
    thread.daemon = True
    thread.start()         


def login_view(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = UserProfile.objects.get(username=username)

            if check_password(password, user.password):

                if user.status != 'Approved':
                    return render(request, 'projectApp/login.html', {
                        'error': 'Your account is waiting for manager approval.'
                    })

                request.session['user_id'] = user.id

                if user.role == 'school_staff':
                    return redirect('/school-staff/')

                if user.role in ['programme_manager', 'manager']:
                    return redirect('/manager-dashboard/')

                return redirect('/dashboard/')

            return render(request, 'projectApp/login.html', {
                'error': 'Incorrect password.'
            })

        except UserProfile.DoesNotExist:

            return render(request, 'projectApp/login.html', {
                'error': 'Username does not exist.'
            })

    return render(request, 'projectApp/login.html')

def register_view(request):

    if request.method == 'POST':

        full_name = request.POST.get('fullname')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm-password')
        role = request.POST.get('role')
        school = request.POST.get('school')
        phone = request.POST.get('phone')
        learners = request.POST.get('learners')

        if password != confirm_password:

            return render(request, 'projectApp/register.html', {
                'error': 'Passwords do not match.'
            })

        if UserProfile.objects.filter(username=username).exists():

            return render(request, 'projectApp/register.html', {
                'error': 'Username already exists.'
            })

        if UserProfile.objects.filter(email=email).exists():

            return render(request, 'projectApp/register.html', {
                'error': 'Email already exists.'
            })

        new_user = UserProfile.objects.create(
            full_name=full_name.strip() if full_name else '',
            username=username.strip() if username else '',
            email=email.strip() if email else '',
            password=make_password(password),
            role=role,
            school=school.strip() if school else None,
            phone=phone.strip() if phone else None,
            learners=int(learners) if learners else None,
            status='Pending'
        )
        send_email_async(
            'NSNP Registration Received',
            f'''Hello {new_user.full_name},

Thank you for registering for the National School Nutrition Programme Food Tracking System.

We have received your registration request.

Your account is now pending review by a programme manager. You will receive a follow-up email once your request has been approved or declined.

If you have any questions in the meantime, please contact your programme administrator.

Thank you for your interest.

Kind regards,
NSNP Food Tracking System
''',
            'nsnpfoodtracking@gmail.com',
            [new_user.email],
        )

        
        return render(request, 'projectApp/login.html', {
            'success': 'Registration submitted successfully. Your account is waiting for manager approval. A confirmation email has been sent.'
        })

    return render(request, 'projectApp/register.html')

def approve_user_view(request, user_id):

    manager = get_logged_in_user(request)

    if not manager:
        return redirect('/')

    if manager.role not in ['programme_manager', 'manager']:
        return redirect('/dashboard/')

    try:
        account = UserProfile.objects.get(id=user_id)

    except UserProfile.DoesNotExist:
        return redirect('/user-management/')

    if request.method == 'POST':

        account.status = 'Approved'
        account.save()

        send_mail(
            'NSNP Account Approved — You Can Now Sign In',
            f'''Hello {account.full_name},

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NSNP FOOD TRACKING SYSTEM
  Account Approved
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Great news! Your registration for the National School Nutrition Programme Food Tracking System has been approved.

► Your Access Details
  Username: {account.username}
  Role: {account.role.replace("_", " ").title()}

► Next Steps
  1. Visit the login page: http://127.0.0.1:8000/
  2. Sign in with your username and password.
  3. You will be taken to your role-specific dashboard.

If you have any questions, please contact your programme administrator.

Welcome aboard!

Kind regards,
NSNP Food Tracking System
Department of Basic Education · South Africa
''',
            'nsnpfoodtracking@gmail.com',
            [account.email],
            fail_silently=True
        )

    return redirect('/user-management/')

def reject_user_view(request, user_id):

    manager = get_logged_in_user(request)

    if not manager:
        return redirect('/')

    if manager.role not in ['programme_manager', 'manager']:
        return redirect('/dashboard/')

    try:
        account = UserProfile.objects.get(id=user_id)

    except UserProfile.DoesNotExist:
        return redirect('/user-management/')

    if request.method == 'POST':

        account.status = 'Rejected'
        account.save()

        send_mail(
            'NSNP Registration Update',
            f'''Hello {account.full_name},

Thank you for registering for the National School Nutrition Programme Food Tracking System.

Your registration request has not been approved at this time.

Thank you.
''',
            'nsnpfoodtracking@gmail.com',
            [account.email],
            fail_silently=True
        )

    return redirect('/user-management/')


def dashboard_view(request):
    user = get_logged_in_user(request)

    if not user:
        return redirect('login')

    if user.role not in ['driver', 'delivery_driver']:
        return redirect('login')

    today = timezone.localdate()

    deliveries = Delivery.objects.filter(driver=user).order_by('-delivery_date', '-id')

    today_deliveries = deliveries.filter(delivery_date=today).count()

    completed = deliveries.filter(
        delivery_date=today,
        status='Completed'
    ).count()

    pending = deliveries.filter(
        delivery_date=today,
        status='Pending'
    ).count()

    total_items = sum(delivery.quantity for delivery in deliveries)

    if today_deliveries > 0:
        completion_percentage = round((completed / today_deliveries) * 100)
    else:
        completion_percentage = 0

    next_delivery = deliveries.filter(
        status='Pending'
    ).order_by('delivery_date', 'delivery_time', 'id').first()

    issues = Issue.objects.filter(
        reported_by=user
    ).select_related(
        'delivery'
    ).order_by('-created_at')

    unread_notifications = Notification.objects.filter(
        user=user,
        is_read=False
    ).count()

    if request.method == 'POST':

        school = request.POST.get('school')
        food_item = request.POST.get('food')
        quantity = request.POST.get('quantity')
        delivery_date = request.POST.get('date')

        if school and food_item and quantity and delivery_date:

            try:
                quantity = int(quantity)

                if quantity > 0:

                 Delivery.objects.create(
                        school=school.strip() if school else '',
                        food_item=food_item.strip() if food_item else '',
                        quantity=quantity,
                        delivery_date=delivery_date,
                        driver=user,
                        status='Pending'
                    )

                 Notification.objects.create(
                        user=user,
                        message=f'Delivery to {school} logged successfully.',
                        notification_type='delivery'
                    )

                 return redirect('/dashboard/')

            except (ValueError, TypeError):
                pass

        return render(request, 'projectApp/driver_dashboard.html', {
            'user': user,
            'deliveries': deliveries,
            'today_date': today,
            'today_deliveries': today_deliveries,
            'completed': completed,
            'pending': pending,
            'total_items': total_items,
            'completion_percentage': completion_percentage,
            'next_delivery': next_delivery,
            'issues': issues,
            'unread_notifications': unread_notifications,
            'error': 'Please complete all delivery fields with valid values.'
        })

    return render(request, 'projectApp/driver_dashboard.html', {
        'user': user,
        'deliveries': deliveries,
        'today_date': today,
        'today_deliveries': today_deliveries,
        'completed': completed,
        'pending': pending,
        'total_items': total_items,
        'completion_percentage': completion_percentage,
        'next_delivery': next_delivery,
        'issues': issues,
        'unread_notifications': unread_notifications
    })

def update_delivery_status_view(request, delivery_id):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    if user.role not in ['driver', 'delivery_driver']:
        return redirect('/dashboard/')

    try:
        delivery = Delivery.objects.get(
            id=delivery_id,
            driver=user
        )

    except Delivery.DoesNotExist:
        return redirect('/dashboard/')

    if request.method == 'POST':

        new_status = request.POST.get('status')

        if new_status not in ['Completed', 'Delayed']:
            return redirect('/dashboard/')

        delivery.status = new_status
        delivery.save()

        if new_status == 'Completed':

            clean_school_name = delivery.school.strip()

            inventory_item = Inventory.objects.filter(
                school__iexact=clean_school_name,
                food_item=delivery.food_item
            ).first()

            if inventory_item:

                inventory_item.quantity += delivery.quantity
                inventory_item.save()

            else:

                inventory_item = Inventory.objects.create(
                    school=clean_school_name,
                    food_item=delivery.food_item,
                    category='Other',
                    quantity=delivery.quantity,
                    minimum_stock=10
                )

            check_and_alert_low_stock(inventory_item, clean_school_name)

        clean_school = delivery.school.strip().lower()

        staff_users = UserProfile.objects.filter(
            role='school_staff',
            status='Approved'
        )

        for staff in staff_users:

            staff_school = (staff.school or '').strip().lower()

            if staff_school == clean_school:

                Notification.objects.create(
                    user=staff,
                    message=f'Delivery of {delivery.food_item} ({delivery.quantity} units) from {delivery.driver.full_name} is now {new_status}.',
                    notification_type='delivery'
                )

    return redirect('/dashboard/')

def manager_dashboard_view(request):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    if user.role not in ['programme_manager', 'manager']:

        if user.role == 'school_staff':
            return redirect('/school-staff/')

        if user.role in ['driver', 'delivery_driver']:
            return redirect('/dashboard/')

        return redirect('/')

    today = timezone.localdate()

    deliveries = Delivery.objects.all().order_by('-delivery_date', '-id')

    issues = Issue.objects.select_related('delivery', 'reported_by').order_by('-created_at')

    inventory = Inventory.objects.all()

    total_schools = Delivery.objects.values('school').distinct().count()

    active_drivers = UserProfile.objects.filter(
        role__in=['driver', 'delivery_driver']
    ).count()

    deliveries_today = deliveries.filter(delivery_date=today).count()

    completed_today = deliveries.filter(delivery_date=today, status='Completed').count()

    pending_today = deliveries.filter(delivery_date=today, status='Pending').count()

    delayed_today = deliveries.filter(delivery_date=today, status='Delayed').count()

    total_deliveries = deliveries.count()

    completed_deliveries = deliveries.filter(status='Completed').count()

    if total_deliveries > 0:
        completion_rate = round((completed_deliveries / total_deliveries) * 100, 1)
    else:
        completion_rate = 0

    open_issues = issues.filter(status='Open').count()

    in_progress_issues = issues.filter(status='In Progress').count()

    resolved_issues = issues.filter(status='Resolved').count()

    school_names = list(deliveries.values_list('school', flat=True).distinct())

    school_delivery_data = []

    for school in school_names:

        delivered = deliveries.filter(school=school, status='Completed').count()

        pending = deliveries.filter(school=school, status='Pending').count()

        delayed = deliveries.filter(school=school, status='Delayed').count()

        school_delivery_data.append({
            'school': school,
            'delivered': delivered,
            'pending': pending,
            'delayed': delayed
        })

    week_start = today - timedelta(days=today.weekday())

    weekly_delivery_data = []

    for day_number in range(5):

        current_day = week_start + timedelta(days=day_number)

        delivery_count = deliveries.filter(delivery_date=current_day).count()

        weekly_delivery_data.append({
            'day': current_day.strftime('%a'),
            'date': current_day,
            'deliveries': delivery_count,
            'target': 150
        })

    recent_issues = issues[:5]

    for issue in recent_issues:

        issue.display_id = f'ISS-{issue.id:04d}'

        if issue.status == 'Resolved':
            issue.display_status = 'Resolved'
            issue.status_class = 'resolved'

        elif issue.status == 'In Progress':
            issue.display_status = 'In Progress'
            issue.status_class = 'in-progress'

        else:
            issue.display_status = 'Pending'
            issue.status_class = 'pending'

    live_deliveries = deliveries.filter(delivery_date=today)[:5]

    for delivery in live_deliveries:

        if delivery.status == 'Completed':
            delivery.display_status = 'Completed'
            delivery.status_class = 'completed'

        elif delivery.status == 'Delayed':
            delivery.display_status = 'Delayed'
            delivery.status_class = 'delayed'

        else:
            delivery.display_status = 'Pending'
            delivery.status_class = 'pending'

    notifications = Notification.objects.filter(user=user)

    unread_count = notifications.filter(is_read=False).count()

    low_stock_items = inventory.filter(
        quantity__lt=models.F('minimum_stock')
    ).count()

    low_stock_count = low_stock_items

    meals_served = completed_deliveries * 300

    pending_registration_count = UserProfile.objects.filter(status='Pending').count()

    # ============== SCHOOL PERFORMANCE ==============

    school_performance = []

    for school in school_names:

        school_deliveries = deliveries.filter(school=school)

        total_school_deliveries = school_deliveries.count()

        completed_school_deliveries = school_deliveries.filter(
            status='Completed'
        ).count()

        if total_school_deliveries > 0:
            on_time = int(
                (completed_school_deliveries / total_school_deliveries) * 100
            )
        else:
            on_time = 0

        compliance = on_time

        meals = completed_school_deliveries * 300

        if on_time >= 85:
            status = 'Excellent'
        elif on_time >= 65:
            status = 'Good'
        else:
            status = 'Warning'

        school_performance.append({
            'name': school,
            'on_time': on_time,
            'compliance': compliance,
            'meals': meals,
            'status': status,
        })


    DISTRICT_NAMES = ['Capricorn', 'Waterberg', 'Mopani', 'Sekhukhune', 'Vhembe']

    district_compliance_data = []

    for district_name in DISTRICT_NAMES:

        district_deliveries = deliveries.filter(district__iexact=district_name)

        total_district = district_deliveries.count()

        compliant_district = district_deliveries.filter(status='Completed').count()

        if total_district > 0:
            compliance_percentage = int(
                (compliant_district / total_district) * 100
            )
        else:
            compliance_percentage = 0

        district_compliance_data.append({
            'name': district_name,
            'total': total_district,
            'compliant': compliant_district,
            'percentage': compliance_percentage,
        })

    if district_compliance_data:
        max_total = max(d['total'] for d in district_compliance_data)
        if max_total == 0:
            max_total = 1
    else:
        max_total = 1

    for d in district_compliance_data:
        d['total_height'] = int((d['total'] / max_total) * 100)
        d['compliant_height'] = int((d['compliant'] / max_total) * 100)

    context = {
        'user': user,
        'today': today,
        'total_schools': total_schools,
        'active_drivers': active_drivers,
        'deliveries_today': deliveries_today,
        'completed_today': completed_today,
        'pending_today': pending_today,
        'delayed_today': delayed_today,
        'total_deliveries': total_deliveries,
        'completion_rate': completion_rate,
        'open_issues': open_issues,
        'in_progress_issues': in_progress_issues,
        'resolved_issues': resolved_issues,
        'low_stock_items': low_stock_items,
        'weekly_delivery_data': weekly_delivery_data,
        'school_delivery_data': school_delivery_data,
        'recent_issues': recent_issues,
        'live_deliveries': live_deliveries,
        'unread_count': unread_count,
        'pending_registration_count': pending_registration_count,
        'school_performance': school_performance,
        'district_compliance_data': district_compliance_data,
        'low_stock_count': low_stock_count,
        'meals_served': meals_served,
    }

    return render(request, 'projectApp/manager_dashboard.html', context)
def logout_view(request):

    request.session.flush()

    return redirect('/')

def create_delivery_view(request):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    if user.role not in ['programme_manager', 'manager']:
        return redirect('/dashboard/')

    drivers = UserProfile.objects.filter(
        role__in=['driver', 'delivery_driver'],
        status='Approved'
    ).order_by('full_name')

    error_message = None

    if request.method == 'POST':

        school = request.POST.get('school')
        district = request.POST.get('district')            # 👈 ADD
        food_item = request.POST.get('food_item')
        quantity = request.POST.get('quantity')
        delivery_date = request.POST.get('delivery_date')
        delivery_time = request.POST.get('delivery_time')
        driver_id = request.POST.get('driver')
        recipient_name = request.POST.get('recipient_name')

        try:

            quantity = int(quantity)

            if quantity <= 0:
                raise ValueError

            driver = UserProfile.objects.get(
                id=driver_id,
                role__in=['driver', 'delivery_driver']
            )
            
            Delivery.objects.create(
                school=school.strip() if school else '',
                district=district.strip() if district else 'Capricorn',  # 👈 ADD
                food_item=food_item.strip() if food_item else '',
                quantity=quantity,
                delivery_date=delivery_date,
                delivery_time=delivery_time if delivery_time else None,
                recipient_name=recipient_name.strip() if recipient_name else None,
                driver=driver,
                status='Pending'
            )

            Notification.objects.create(
                user=driver,
                message=f'New delivery assigned: {quantity} x {food_item} to {school}.',
                notification_type='delivery'
            )

            return redirect('/deliveries/create/')

        except (ValueError, TypeError):

            error_message = 'Please enter a valid quantity.'

        except UserProfile.DoesNotExist:

            error_message = 'Selected driver does not exist.'

    recent_deliveries = Delivery.objects.all().order_by(
        '-delivery_date', '-id'
    )[:10]

    for delivery in recent_deliveries:

        if delivery.status == 'Completed':
            delivery.display_status = 'Delivered'
            delivery.status_class = 'completed'

        elif delivery.status == 'Delayed':
            delivery.display_status = 'Delayed'
            delivery.status_class = 'delayed'

        else:
            delivery.display_status = 'Pending'
            delivery.status_class = 'pending'

    unread_count = Notification.objects.filter(
        user=user,
        is_read=False
    ).count()

    return render(
        request,
        'projectApp/create_delivery.html',
        {
            'user': user,
            'drivers': drivers,
            'recent_deliveries': recent_deliveries,
            'unread_count': unread_count,
            'error': error_message
        }
    )

def school_staff_view(request):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    if user.role != 'school_staff':

        if user.role in ['programme_manager', 'manager']:
            return redirect('/manager-dashboard/')

        if user.role in ['driver', 'delivery_driver']:
            return redirect('/dashboard/')

        return redirect('/')

    school_name = (user.school or 'Greenfield Primary School').strip()
    today = timezone.localdate()

    if request.method == 'POST':

        delivery_id = request.POST.get('delivery_id')

        if delivery_id:

            try:

                delivery = Delivery.objects.get(
                    id=delivery_id,
                    school__iexact=school_name,
                    status__iexact='Pending'
                )

                delivery.status = 'Completed'
                delivery.save()

                inventory_item = Inventory.objects.filter(
                    school__iexact=school_name,
                    food_item=delivery.food_item
                ).first()

                if inventory_item:

                    inventory_item.quantity += delivery.quantity
                    inventory_item.save()

                else:

                    inventory_item = Inventory.objects.create(
                        school=school_name,
                        food_item=delivery.food_item,
                        category='Other',
                        quantity=delivery.quantity,
                        minimum_stock=10
                    )

                check_and_alert_low_stock(inventory_item, school_name)

            except Delivery.DoesNotExist:

                pass

        return redirect('/school-staff/')

    deliveries = Delivery.objects.filter(
        school__iexact=school_name
    ).order_by('-delivery_date', '-id')

    pending_deliveries = deliveries.filter(status__iexact='Pending')

    total_deliveries = deliveries.count()

    pending_count = pending_deliveries.count()

    completed_count = deliveries.filter(status__iexact='Completed').count()

    inventory = Inventory.objects.filter(
        school__iexact=school_name
    ).order_by('food_item')

    low_stock = inventory.filter(quantity__lt=models.F('minimum_stock'))

    for item in inventory:

        if item.minimum_stock > 0:

            item.stock_level = min(
                int((item.quantity / item.minimum_stock) * 100),
                100
            )

        else:

            item.stock_level = 100

        if item.quantity < item.minimum_stock:
            item.status = 'Low Stock'
        else:
            item.status = 'Adequate'

    latest_inventory = inventory.order_by('-updated_at').first()

    total_inventory = sum(item.quantity for item in inventory)

    notifications = Notification.objects.filter(user=user)

    unread_count = notifications.filter(is_read=False).count()

    issues = Issue.objects.filter(
        reported_by=user
    ).select_related('delivery').order_by('-created_at')

    week_start = today - timedelta(days=today.weekday())

    week_end = week_start + timedelta(days=4)

    daily_usage = []

    for day_number in range(5):

        current_day = week_start + timedelta(days=day_number)

        day_deliveries = deliveries.filter(delivery_date=current_day)

        rice_quantity = 0
        beans_quantity = 0
        oil_quantity = 0

        for delivery in day_deliveries:

            food_name = delivery.food_item.lower()

            if 'rice' in food_name:
                rice_quantity += delivery.quantity

            elif 'bean' in food_name:
                beans_quantity += delivery.quantity

            elif 'oil' in food_name:
                oil_quantity += delivery.quantity

        daily_usage.append({
            'date': current_day,
            'day': current_day.strftime('%a'),
            'rice': rice_quantity,
            'beans': beans_quantity,
            'oil': oil_quantity
        })

    usage_values = []

    for day in daily_usage:

        usage_values.append(day['rice'])
        usage_values.append(day['beans'])
        usage_values.append(day['oil'])

    maximum_usage = max(usage_values) if usage_values else 0

    if maximum_usage == 0:
        maximum_usage = 1

    for day in daily_usage:

        day['rice_height'] = min(int((day['rice'] / maximum_usage) * 100), 100)
        day['beans_height'] = min(int((day['beans'] / maximum_usage) * 100), 100)
        day['oil_height'] = min(int((day['oil'] / maximum_usage) * 100), 100)

    weekly_usage_total = sum(
        day['rice'] + day['beans'] + day['oil']
        for day in daily_usage
    )

    context = {
        'user': user,
        'today': today,
        'school_name': school_name,
        'total_deliveries': total_deliveries,
        'pending_count': pending_count,
        'completed_count': completed_count,
        'total_inventory': total_inventory,
        'weekly_usage_total': weekly_usage_total,
        'low_stock': low_stock,
        'pending_deliveries': pending_deliveries,
        'inventory': inventory,
        'latest_inventory': latest_inventory,
        'unread_count': unread_count,
        'issues': issues,
        'week_start': week_start,
        'week_end': week_end,
        'daily_usage': daily_usage,
        'maximum_usage': maximum_usage,
        'learners_fed': 312,
    }

    return render(request, 'projectApp/school_staff.html', context)

def report_issue_view(request):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    if user.role in ['driver', 'delivery_driver']:
        deliveries = Delivery.objects.filter(driver=user).order_by('-delivery_date', '-id')
    elif user.role == 'school_staff':
        deliveries = Delivery.objects.filter(
            school__iexact=user.school or ''
        ).order_by('-delivery_date', '-id')
    else:
        deliveries = Delivery.objects.all().order_by('-delivery_date', '-id')

    if request.method == 'POST':

        issue_type = request.POST.get('issue_type')
        delivery_id = request.POST.get('delivery')
        priority = request.POST.get('priority', 'Medium')
        description = request.POST.get('description')
        picture = request.FILES.get('picture')

        if priority not in ['Low', 'Medium', 'High']:
            priority = 'Medium'

        if not issue_type or not delivery_id or not description:

            return render(
                request,
                'projectApp/report_issue.html',
                {
                    'user': user,
                    'deliveries': deliveries,
                    'error': 'Please complete all required fields.',
                    'today': timezone.localdate()
                }
            )

        try:
            delivery = Delivery.objects.get(id=delivery_id)

        except Delivery.DoesNotExist:

            return render(
                request,
                'projectApp/report_issue.html',
                {
                    'user': user,
                    'deliveries': deliveries,
                    'error': 'The selected delivery does not exist.',
                    'today': timezone.localdate()
                }
            )

        if picture:

            allowed_types = ['image/jpeg', 'image/png', 'application/pdf']

            if picture.content_type not in allowed_types:

                return render(
                    request,
                    'projectApp/report_issue.html',
                    {
                        'user': user,
                        'deliveries': deliveries,
                        'error': 'Only PNG, JPG, JPEG and PDF files are allowed.',
                        'today': timezone.localdate()
                    }
                )

            if picture.size > 10 * 1024 * 1024:

                return render(
                    request,
                    'projectApp/report_issue.html',
                    {
                        'user': user,
                        'deliveries': deliveries,
                        'error': 'The attached file must be smaller than 10 MB.',
                        'today': timezone.localdate()
                    }
                )

        issue = Issue.objects.create(
            delivery=delivery,
            reported_by=user,
            issue_type=issue_type,
            priority=priority,
            description=description,
            picture=picture,
            status='Open'
        )

        Notification.objects.create(
            user=user,
            message=f'Issue report {issue.id} has been submitted.',
            notification_type='system'
        )

        return redirect('/report-issue/')

    issues = Issue.objects.select_related('delivery', 'reported_by').order_by('-created_at')

    total_issues = issues.count()

    resolved_issues = issues.filter(status='Resolved').count()

    in_progress_issues = issues.filter(status='In Progress').count()

    pending_issues = issues.filter(status='Open').count()

    if total_issues > 0:
        resolution_rate = int((resolved_issues / total_issues) * 100)
    else:
        resolution_rate = 0

    for issue in issues:

        issue.display_id = f'ISS-{issue.id:04d}'

        if issue.status == 'Resolved':
            issue.display_status = 'Resolved'
            issue.status_class = 'resolved'

        elif issue.status == 'In Progress':
            issue.display_status = 'In Progress'
            issue.status_class = 'in-progress'

        else:
            issue.display_status = 'Pending'
            issue.status_class = 'pending'

    notifications = Notification.objects.filter(user=user)

    unread_notifications = notifications.filter(is_read=False).count()

    return render(
        request,
        'projectApp/report_issue.html',
        {
            'user': user,
            'deliveries': deliveries,
            'issues': issues,
            'total_issues': total_issues,
            'in_progress_issues': in_progress_issues,
            'resolved_issues': resolved_issues,
            'pending_issues': pending_issues,
            'resolution_rate': resolution_rate,
            'unread_notifications': unread_notifications,
            'today': timezone.localdate()
        }
    )

def update_issue_status_view(request, issue_id):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    if user.role not in ['programme_manager', 'manager']:
        return redirect('/dashboard/')

    try:
        issue = Issue.objects.get(id=issue_id)

    except Issue.DoesNotExist:
        return redirect('/report-issue/')

    if request.method == 'POST':

        new_status = request.POST.get('status')

        if new_status not in ['Open', 'In Progress', 'Resolved']:
            return redirect('/report-issue/')

        if issue.status != new_status:

            issue.status = new_status
            issue.save()

            Notification.objects.create(
                user=issue.reported_by,
                message=f'Your issue report #{issue.id} was updated to: {new_status}.',
                notification_type='resolved' if new_status == 'Resolved' else 'system'
            )

    return redirect('/report-issue/')


def reports_view(request):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    if user.role not in ['school_staff', 'programme_manager', 'manager']:
        return redirect('/dashboard/')

    deliveries = Delivery.objects.all().order_by('-delivery_date', '-id')

    issues = Issue.objects.all().order_by('-created_at')

    inventory = Inventory.objects.all().order_by('food_item')

    total_deliveries = deliveries.count()

    completed_deliveries = deliveries.filter(status='Completed').count()

    pending_deliveries = deliveries.filter(status='Pending').count()

    total_issues = issues.count()

    open_issues = issues.filter(status='Open').count()

    resolved_issues = issues.filter(status='Resolved').count()

    total_inventory_items = inventory.count()

    low_stock_items = inventory.filter(quantity__lt=models.F('minimum_stock')).count()

    today = timezone.localdate()

    expiring_items = 0

    for item in inventory:

        if item.expiry_date:

            days_until_expiry = (item.expiry_date - today).days

            if 0 <= days_until_expiry <= 10:
                expiring_items += 1

    if total_deliveries > 0:
        completion_rate = round((completed_deliveries / total_deliveries) * 100, 1)
    else:
        completion_rate = 0

    if total_issues > 0:
        resolution_rate = round((resolved_issues / total_issues) * 100, 1)
    else:
        resolution_rate = 0

    total_inventory_quantity = sum(item.quantity for item in inventory)

    delivery_labels = []
    delivery_completed_data = []
    delivery_pending_data = []

    for delivery in deliveries.order_by('delivery_date'):

        date_label = delivery.delivery_date.strftime('%d %b')

        if date_label not in delivery_labels:

            delivery_labels.append(date_label)

            completed_count = deliveries.filter(
                delivery_date=delivery.delivery_date,
                status='Completed'
            ).count()

            pending_count = deliveries.filter(
                delivery_date=delivery.delivery_date,
                status='Pending'
            ).count()

            delivery_completed_data.append(completed_count)
            delivery_pending_data.append(pending_count)

    inventory_labels = []
    inventory_data = []

    inventory_by_date = {}

    for item in inventory:

        date_label = item.updated_at.strftime('%b %Y')

        if date_label not in inventory_by_date:
            inventory_by_date[date_label] = 0

        inventory_by_date[date_label] += item.quantity

    for date_label, quantity in inventory_by_date.items():

        inventory_labels.append(date_label)
        inventory_data.append(quantity)

    recent_reports = [
        {'name': 'Delivery Report', 'type': 'Delivery', 'date': today, 'format': 'PDF'},
        {'name': 'Inventory Report', 'type': 'Inventory', 'date': today, 'format': 'Excel'},
        {'name': 'Issues Report', 'type': 'Issues', 'date': today, 'format': 'CSV'}
    ]

    unread_notifications = Notification.objects.filter(
        user=user,
        is_read=False
    ).count()

    return render(
        request,
        'projectApp/reports.html',
        {
            'user': user,
            'deliveries': deliveries,
            'issues': issues,
            'inventory': inventory,
            'total_deliveries': total_deliveries,
            'completed_deliveries': completed_deliveries,
            'pending_deliveries': pending_deliveries,
            'total_issues': total_issues,
            'open_issues': open_issues,
            'resolved_issues': resolved_issues,
            'total_inventory_items': total_inventory_items,
            'low_stock_items': low_stock_items,
            'expiring_items': expiring_items,
            'total_inventory_quantity': total_inventory_quantity,
            'completion_rate': completion_rate,
            'resolution_rate': resolution_rate,
            'delivery_labels': delivery_labels,
            'delivery_completed_data': delivery_completed_data,
            'delivery_pending_data': delivery_pending_data,
            'inventory_labels': inventory_labels,
            'inventory_data': inventory_data,
            'recent_reports': recent_reports,
            'unread_notifications': unread_notifications
        }
    )

def download_report_view(request):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    report_type = request.GET.get('report_type', 'delivery')
    report_format = request.GET.get('format', 'PDF')

    date_from = request.GET.get('date_from') or None
    date_to = request.GET.get('date_to') or None

    date_range = request.GET.get('date_range', '')

    today = timezone.localdate()

    if date_range == 'this-week':
        date_from = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

    elif date_range == 'last-6-weeks':
        date_from = (today - timedelta(weeks=6)).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

    elif date_range == 'this-month':
        date_from = today.replace(day=1).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

    elif date_range == 'last-quarter':
        date_from = (today - timedelta(days=90)).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')

    deliveries = Delivery.objects.all().order_by('-delivery_date', '-id')
    issues = Issue.objects.all().order_by('-created_at')
    inventory = Inventory.objects.all().order_by('food_item')

    if date_from:
        try:
            date_from_object = datetime.strptime(date_from, '%Y-%m-%d').date()
            deliveries = deliveries.filter(delivery_date__gte=date_from_object)
            issues = issues.filter(created_at__date__gte=date_from_object)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_object = datetime.strptime(date_to, '%Y-%m-%d').date()
            deliveries = deliveries.filter(delivery_date__lte=date_to_object)
            issues = issues.filter(created_at__date__lte=date_to_object)
        except ValueError:
            pass

    if report_format == 'CSV':

        response = HttpResponse(content_type='text/csv')
        filename = report_type + '_report.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        if report_type == 'delivery':
            writer.writerow(['School', 'Food Item', 'Quantity', 'Delivery Date', 'Driver', 'Status'])
            for delivery in deliveries:
                writer.writerow([
                    delivery.school,
                    delivery.food_item,
                    delivery.quantity,
                    delivery.delivery_date,
                    delivery.driver.full_name,
                    delivery.status
                ])

        elif report_type == 'inventory':
            writer.writerow(['School', 'Food Item', 'Category', 'Quantity', 'Minimum Stock', 'Expiry Date', 'Batch Reference'])
            for item in inventory:
                writer.writerow([
                    item.school,
                    item.food_item,
                    item.category,
                    item.quantity,
                    item.minimum_stock,
                    item.expiry_date,
                    item.batch_reference
                ])

        elif report_type == 'issues':
            writer.writerow(['School', 'Food Item', 'Issue Type', 'Description', 'Reported By', 'Status', 'Created At'])
            for issue in issues:
                writer.writerow([
                    issue.delivery.school,
                    issue.delivery.food_item,
                    issue.issue_type,
                    issue.description,
                    issue.reported_by.full_name,
                    issue.status,
                    issue.created_at
                ])

        return response

    if report_format == 'Excel':

        try:
            from openpyxl import Workbook
        except ImportError:
            return HttpResponse('Excel export requires openpyxl to be installed. Run: pip install openpyxl')

        workbook = Workbook()
        worksheet = workbook.active

        if report_type == 'delivery':
            worksheet.title = 'Delivery Report'
            worksheet.append(['School', 'Food Item', 'Quantity', 'Delivery Date', 'Driver', 'Status'])
            for delivery in deliveries:
                worksheet.append([
                    delivery.school,
                    delivery.food_item,
                    delivery.quantity,
                    delivery.delivery_date,
                    delivery.driver.full_name,
                    delivery.status
                ])

        elif report_type == 'inventory':
            worksheet.title = 'Inventory Report'
            worksheet.append(['School', 'Food Item', 'Category', 'Quantity', 'Minimum Stock', 'Expiry Date', 'Batch Reference'])
            for item in inventory:
                worksheet.append([
                    item.school,
                    item.food_item,
                    item.category,
                    item.quantity,
                    item.minimum_stock,
                    item.expiry_date,
                    item.batch_reference
                ])

        elif report_type == 'issues':
            worksheet.title = 'Issues Report'
            worksheet.append(['School', 'Food Item', 'Issue Type', 'Description', 'Reported By', 'Status', 'Created At'])
            for issue in issues:
                worksheet.append([
                    issue.delivery.school,
                    issue.delivery.food_item,
                    issue.issue_type,
                    issue.description,
                    issue.reported_by.full_name,
                    issue.status,
                    issue.created_at
                ])

        for column in worksheet.columns:
            maximum_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                if cell.value:
                    length = len(str(cell.value))
                    if length > maximum_length:
                        maximum_length = length
            worksheet.column_dimensions[column_letter].width = maximum_length + 3

        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = report_type + '_report.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    if report_format == 'PDF':

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import (
                SimpleDocTemplate,
                Table,
                TableStyle,
                Paragraph,
                Spacer
            )
        except ImportError:
            return HttpResponse('PDF export requires reportlab to be installed. Run: pip install reportlab')

        output = BytesIO()
        document = SimpleDocTemplate(output, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        if report_type == 'delivery':
            title = 'NSNP Delivery Report'
            data = [['School', 'Food Item', 'Qty', 'Date', 'Driver', 'Status']]
            for delivery in deliveries:
                data.append([
                    delivery.school,
                    delivery.food_item,
                    str(delivery.quantity),
                    str(delivery.delivery_date),
                    delivery.driver.full_name,
                    delivery.status
                ])

        elif report_type == 'inventory':
            title = 'NSNP Inventory Report'
            data = [['School', 'Food Item', 'Category', 'Quantity', 'Minimum']]
            for item in inventory:
                data.append([
                    item.school,
                    item.food_item,
                    item.category,
                    str(item.quantity),
                    str(item.minimum_stock)
                ])

        else:
            title = 'NSNP Issues Report'
            data = [['School', 'Issue Type', 'Reported By', 'Status', 'Date']]
            for issue in issues:
                data.append([
                    issue.delivery.school,
                    issue.issue_type,
                    issue.reported_by.full_name,
                    issue.status,
                    issue.created_at.strftime('%d %b %Y')
                ])

        elements.append(Paragraph(title, styles['Title']))
        elements.append(Spacer(1, 20))

        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
            ])
        )
        elements.append(table)

        document.build(elements)
        output.seek(0)

        response = HttpResponse(output.getvalue(), content_type='application/pdf')
        filename = report_type + '_report.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    return redirect('/reports/')

def notifications_view(request):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    if request.method == 'POST':

        action = request.POST.get('action')
        notification_id = request.POST.get('notification_id')

        if action == 'mark_all_read':

            Notification.objects.filter(
                user=user,
                is_read=False
            ).update(is_read=True)

        elif action == 'mark_read' and notification_id:

            Notification.objects.filter(
                id=notification_id,
                user=user
            ).update(is_read=True)

        elif action == 'delete' and notification_id:

            Notification.objects.filter(
                id=notification_id,
                user=user
            ).delete()

        return redirect('/notifications/')

    current_filter = request.GET.get('filter', 'all')

    all_notifications = Notification.objects.filter(
        user=user
    ).order_by('-created_at')

    unread_count = all_notifications.filter(is_read=False).count()

    alert_count = all_notifications.filter(
        notification_type__in=['alert', 'expiry']
    ).count()

    today = timezone.localdate()

    today_count = all_notifications.filter(
        created_at__date=today
    ).count()

    critical_notifications = all_notifications.filter(
        notification_type__in=['alert', 'expiry']
    )[:4]

    recent_activity = all_notifications.filter(
        notification_type__in=['delivery', 'resolved']
    )[:4]

    if current_filter == 'unread':

        notifications = all_notifications.filter(is_read=False)

    elif current_filter in ['Stock', 'Delivery', 'System']:

        if current_filter == 'Stock':

            notifications = all_notifications.filter(
                notification_type__in=['alert', 'expiry']
            )

        elif current_filter == 'Delivery':

            notifications = all_notifications.filter(
                notification_type__in=['delivery', 'delay']
            )

        else:

            notifications = all_notifications.filter(
                notification_type__in=['resolved', 'system']
            )

    else:

        notifications = all_notifications

    issue_alert_count = all_notifications.filter(
        notification_type__in=['issue', 'system']
    ).count()

    stock_alert_count = all_notifications.filter(
        notification_type__in=['alert', 'expiry']
    ).count()

    context = {
        'user': user,
        'notifications': notifications,
        'unread_count': unread_count,
        'alert_count': alert_count,
        'today_count': today_count,
        'current_filter': current_filter,
        'critical_notifications': critical_notifications,
        'recent_activity': recent_activity,
        'issue_alert_count': issue_alert_count,
        'stock_alert_count': stock_alert_count,
    }

    return render(
        request,
        'projectApp/notifications.html',
        context
    )

def user_management_view(request):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    if user.role not in ['programme_manager', 'manager']:
        return redirect('/dashboard/')

    users = UserProfile.objects.all().order_by('status', 'full_name')

    for account in users:

        account.delivery_count = Delivery.objects.filter(
            driver=account
        ).count()

    total_users = users.count()

    pending_count = users.filter(status='Pending').count()

    approved_count = users.filter(status='Approved').count()

    rejected_count = users.filter(status='Rejected').count()

    school_staff_count = users.filter(role='school_staff').count()

    driver_count = users.filter(
        role__in=['driver', 'delivery_driver']
    ).count()

    manager_count = users.filter(
        role__in=['manager', 'programme_manager']
    ).count()

    unread_count = Notification.objects.filter(
        user=user,
        is_read=False
    ).count()

    top_drivers = sorted(
        [
            account for account in users
            if account.role in ['driver', 'delivery_driver']
        ],
        key=lambda account: account.delivery_count,
        reverse=True
    )[:3]

    context = {
        'user': user,
        'users': users,
        'top_drivers': top_drivers,
        'total_users': total_users,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'school_staff_count': school_staff_count,
        'driver_count': driver_count,
        'manager_count': manager_count,
        'unread_count': unread_count
    }

    return render(
        request,
        'projectApp/user_management.html',
        context
    )

def inventory_view(request):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    if user.role not in [
        'school_staff',
        'programme_manager',
        'manager'
    ]:
        return redirect('/dashboard/')

    error_message = None

    if request.method == 'POST':

        school = request.POST.get('school')
        food_item = request.POST.get('food_item')
        category = request.POST.get('category')
        quantity = request.POST.get('quantity')
        minimum_stock = request.POST.get('minimum_stock')
        expiry_date = request.POST.get('expiry_date')
        batch_reference = request.POST.get('batch_reference')

        try:

            quantity = int(quantity)
            minimum_stock = int(minimum_stock)

            if quantity < 0 or minimum_stock < 0:
                error_message = 'Quantities cannot be negative.'

            elif not food_item or not school or not category:
                error_message = 'Please fill in all required fields.'

            else:

                Inventory.objects.create(
                    school=school,
                    food_item=food_item,
                    category=category,
                    quantity=quantity,
                    minimum_stock=minimum_stock,
                    expiry_date=expiry_date if expiry_date else None,
                    batch_reference=batch_reference
                )

                return redirect('/inventory/')

        except (TypeError, ValueError):

            error_message = 'Please enter valid quantities.'

    inventory = Inventory.objects.all().order_by('food_item')

    inventory_data = []

    for item in inventory:

        if item.minimum_stock > 0:

            percentage = int(
                (item.quantity / (item.minimum_stock * 2.5)) * 100
            )

        else:

            percentage = 100

        if percentage > 100:
            percentage = 100

        if item.quantity == 0:

            status = 'Critical'

        elif item.quantity < item.minimum_stock:

            status = 'Low'

        else:

            status = 'Good'

        if item.expiry_date:

            days_until_expiry = (
                item.expiry_date - timezone.localdate()
            ).days

        else:

            days_until_expiry = None

        if item.quantity < item.minimum_stock:

            shortfall = item.minimum_stock - item.quantity

        else:

            shortfall = 0

        inventory_data.append({
            'id': item.id,
            'food_item': item.food_item,
            'school': item.school,
            'category': item.category,
            'quantity': item.quantity,
            'minimum_stock': item.minimum_stock,
            'expiry_date': item.expiry_date,
            'batch_reference': item.batch_reference,
            'updated_at': item.updated_at,
            'percentage': percentage,
            'status': status,
            'days_until_expiry': days_until_expiry,
            'shortfall': shortfall
        })

    low_stock_items = [
        item for item in inventory_data
        if item['quantity'] < item['minimum_stock']
    ]

    critical_items = [
        item for item in inventory_data
        if item['status'] == 'Critical'
    ]

    expiring_items = [
        item for item in inventory_data
        if item['days_until_expiry'] is not None
        and 0 <= item['days_until_expiry'] <= 10
    ]

    unread_count = Notification.objects.filter(
        user=user,
        is_read=False
    ).count()

    return render(
        request,
        'projectApp/inventory.html',
        {
            'user': user,
            'inventory': inventory_data,
            'total_items': len(inventory_data),
            'low_stock': len(low_stock_items),
            'low_stock_count': len(low_stock_items),
            'well_stocked_count': len(inventory_data) - len(low_stock_items),
            'orders_needed': len(low_stock_items),
            'critical_stock': len(critical_items),
            'expiring_soon': len(expiring_items),
            'low_stock_items': low_stock_items,
            'critical_items': critical_items,
            'unread_count': unread_count,
            'error': error_message
        }
    )

def edit_inventory_view(request, inventory_id):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    if user.role not in ['school_staff', 'programme_manager', 'manager']:
        return redirect('/dashboard/')

    try:
        inventory = Inventory.objects.get(id=inventory_id)

    except Inventory.DoesNotExist:
        return redirect('/inventory/')

    if request.method == 'POST':

        school = request.POST.get('school')
        food_item = request.POST.get('food_item')
        category = request.POST.get('category')
        quantity = request.POST.get('quantity')
        minimum_stock = request.POST.get('minimum_stock')
        expiry_date = request.POST.get('expiry_date')
        batch_reference = request.POST.get('batch_reference')

        try:

            quantity = int(quantity)
            minimum_stock = int(minimum_stock)

        except (TypeError, ValueError):

            return render(
                request,
                'projectApp/edit_inventory.html',
                {
                    'user': user,
                    'inventory': inventory,
                    'error': 'Please enter valid quantities.'
                }
            )

        if quantity < 0 or minimum_stock < 0:

            return render(
                request,
                'projectApp/edit_inventory.html',
                {
                    'user': user,
                    'inventory': inventory,
                    'error': 'Quantities cannot be negative.'
                }
            )

        inventory.school = school
        inventory.food_item = food_item
        inventory.category = category
        inventory.quantity = quantity
        inventory.minimum_stock = minimum_stock
        inventory.batch_reference = batch_reference

        if expiry_date:
            inventory.expiry_date = expiry_date
        else:
            inventory.expiry_date = None

        inventory.save()

        return redirect('/inventory/')

    return render(
        request,
        'projectApp/edit_inventory.html',
        {
            'user': user,
            'inventory': inventory
        }
    )


def delete_inventory_view(request, inventory_id):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    if user.role not in ['school_staff', 'programme_manager', 'manager']:
        return redirect('/dashboard/')

    try:

        inventory = Inventory.objects.get(id=inventory_id)

        if request.method == 'POST':
            inventory.delete()

    except Inventory.DoesNotExist:
        pass

    return redirect('/inventory/')


def edit_user_view(request, user_id):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    if user.role not in ['programme_manager', 'manager']:
        return redirect('/dashboard/')

    try:
        account = UserProfile.objects.get(id=user_id)

    except UserProfile.DoesNotExist:
        return redirect('/user-management/')

    if request.method == 'POST':

        account.full_name = request.POST.get('full_name')
        account.username = request.POST.get('username')
        account.email = request.POST.get('email')
        account.role = request.POST.get('role')

        new_school = request.POST.get('school')

        if new_school:
            account.school = new_school

        account.save()

        return redirect('/user-management/')

    return render(
        request,
        'projectApp/edit_user.html',
        {
            'user': user,
            'account': account
        }
    )


def delete_user_view(request, user_id):

    user = get_logged_in_user(request)

    if not user:
        return redirect('/')

    if user.role not in ['programme_manager', 'manager']:
        return redirect('/dashboard/')

    try:
        account = UserProfile.objects.get(id=user_id)

    except UserProfile.DoesNotExist:
        return redirect('/user-management/')

    if request.method == 'POST':
        account.delete()

    return redirect('/user-management/')

