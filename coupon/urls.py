from django.urls import path
from . import views

app_name = 'coupon'

urlpatterns = [

    
    path('', views.coupon_list, name='coupon_list'),  # Adjust to the correct list view if needed
    path('add/', views.add_coupon, name='coupon_add'),
    path('edit/<int:pk>/', views.edit_coupon, name='coupon_edit'),
    path('delete/<int:pk>/', views.delete_coupon, name='coupon_delete'),
    path('apply_coupon', views.apply_coupon, name='apply_coupon'),




]