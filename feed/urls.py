from django.urls import path

from . import views

urlpatterns = [
    path('feed/', views.FeedStockView.as_view(), name='feed_stock'),
    path('feed/purchases/', views.FeedPurchaseListView.as_view(), name='feed_purchase_list'),
    path('feed/purchases/add/', views.FeedPurchaseCreateView.as_view(), name='feed_purchase_add'),
    path('feed/purchases/<int:pk>/edit/',
         views.FeedPurchaseUpdateView.as_view(), name='feed_purchase_edit'),
    path('feed/purchases/<int:pk>/delete/',
         views.FeedPurchaseDeleteView.as_view(), name='feed_purchase_delete'),
    path('flocks/<int:batch_pk>/feed/add/',
         views.FeedConsumptionCreateView.as_view(), name='feed_consumption_add'),
    path('feed/consumption/<int:pk>/edit/',
         views.FeedConsumptionUpdateView.as_view(), name='feed_consumption_edit'),
    path('feed/consumption/<int:pk>/delete/',
         views.FeedConsumptionDeleteView.as_view(), name='feed_consumption_delete'),
]
