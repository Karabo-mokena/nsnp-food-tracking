from django.db import models

class UserProfile(models.Model):
    full_name = models.CharField(max_length=100)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=50)
    school = models.CharField(max_length=200, null=True, blank=True) 
    status = models.CharField(max_length=50, default='Pending')
    phone = models.CharField(max_length=20, null=True, blank=True)
    learners = models.PositiveIntegerField(null=True, blank=True) 

    def __str__(self):
        return self.username

class Delivery(models.Model):
    school = models.CharField(max_length=200)
    district = models.CharField(max_length=100, default='Capricorn')   # 👈 ADD THIS
    food_item = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    delivery_date = models.DateField()
    delivery_time = models.TimeField(null=True, blank=True)
    recipient_name = models.CharField(max_length=100, null=True, blank=True)
    driver = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, default='Pending')

    def __str__(self):
        return f"{self.school} - {self.food_item}"


class Issue(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE)
    reported_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    issue_type = models.CharField(max_length=100)
    priority = models.CharField(max_length=50, default='Medium')
    description = models.TextField()
    picture = models.FileField(upload_to='issue_pictures/', null=True, blank=True)
    status = models.CharField(max_length=50, default='Open')
    created_at = models.DateTimeField(auto_now_add=True)
def __str__(self):
        return f"{self.issue_type} - {self.delivery.school}"

class Notification(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    notification_type = models.CharField(max_length=50)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message


class Inventory(models.Model):
    school = models.CharField(max_length=200)
    food_item = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    minimum_stock = models.PositiveIntegerField(default=10)
    expiry_date = models.DateField(null=True, blank=True)
    batch_reference = models.CharField(max_length=100, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.school} - {self.food_item}"