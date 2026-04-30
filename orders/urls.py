from django.urls import path
from orders import views

app_name='orders'

urlpatterns = [
    
    path('success',views.success,name='success'),
    path('invoice/<int:order_id>/',views.invoice,name='invoice'),
    

]
