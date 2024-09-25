from django.urls import path
from admin_log import views

app_name = 'adminlog'

urlpatterns = [
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('base/', views.base, name='base'),
    path('admin_login/', views.admin_login, name='admin_login'),
    path('admin_logout/', views.admin_logout, name='admin_logout'),

    path('users_list/', views.users_list, name='users_list'),
    path('block_unblock_user/<int:user_id>/', views.block_unblock_user, name='block_unblock_user'),

    path('order_list',views.order_list,name='order_list'),
    path('order_details/<int:order_id>/',views.order_details,name='order_details'),

    

    path('sales_report/',views.sales_report,name='sales_report'),
    
]