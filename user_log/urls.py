from django.urls import path
from user_log import views

app_name = 'userlog'

urlpatterns = [
    
    path('',views.index,name='index'),
    path('user_signup/',views.user_signup, name ='user_signup'),
    path('verify_otp/<int:user_id>/', views.verify_otp, name='verify_otp'),
    path('user_login/',views.user_login,name='user_login'),
    path('user_logout/',views.user_logout,name='user_logout'),


    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp-forgot-password/', views.verify_otp_forgot_password, name='verify_otp_forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),


    path('user_products/',views.user_products,name='user_products'),
    path('product_details/<int:product_id>/', views.product_details, name='product_details'),
    path('about/',views.about, name='about'),


    path('user_profile/',views.user_profile,name = 'user_profile'),
    path('profile/edit/', views.edit_user_profile, name='edit_user_profile'),

    path('user_address_add', views.user_address_add, name='user_address_add'),
    path('address/edit/<int:address_id>/', views.edit_address, name='edit_address'),
    path('address/delete/<int:address_id>/', views.delete_address, name='delete_address'),


    path('orders/', views.user_orders, name='user_orders'),
    path('order/<int:order_id>/', views.order_details, name='order_details'),
    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('order/<int:order_id>/return/', views.return_order, name='return_order'),
    
    path('reset_password/', views.reset_password_request, name='reset_password_request'),
    path('reset_password/verify_otp/', views.reset_password_verify_otp, name='reset_password_verify_otp'),
    path('reset_password/set_new/', views.reset_password_set_new, name='reset_password_set_new'),
    
]
   

