from django.urls import path
from cart import views

app_name = 'cart'

urlpatterns = [
    
    
    path('', views.view_cart, name='view_cart'),
    path('add/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update/<int:cart_item_id>/', views.update_cart, name='update_cart'),
    path('clear/', views.clear_cart, name='clear_cart'),
    path('checkout/', views.cart_checkout, name='cart_checkout'),

    path('order_address/', views.order_address, name='order_address'),
    path('delete_order_address/<int:address_id>/', views.delete_order_address, name='delete_order_address'),

    path('set-default-order_address/<int:address_id>/', views.set_default_order_address, name='set_default_order_address'),
    
    path('wishlist/',views.wishlist, name = 'wishlist'),

]

