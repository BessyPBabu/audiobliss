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
    path('payment/verify/', views.payment_verify, name='payment_verify'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),
    path('repay/<int:order_id>/', views.repay_order, name='repay_order'),


    path('order_address/', views.order_address, name='order_address'),
    path('delete_order_address/<int:address_id>/', views.delete_order_address, name='delete_order_address'),

    path('set-default-order_address/<int:address_id>/', views.set_default_order_address, name='set_default_order_address'),
    
    
    path('wishlist/add/', views.add_to_wishlist, name='add_to_wishlist'),
    path('view_wishlist/', views.view_wishlist, name='view_wishlist'),
    path('wishlist/remove/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('counts/', views.get_counts, name='count'),
    path('toggle-wishlist/', views.toggle_wishlist, name='toggle_wishlist'),
    path('check-wishlist/', views.check_wishlist, name='check_wishlist'),

]

