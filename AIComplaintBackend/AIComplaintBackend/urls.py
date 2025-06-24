from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def home(request):
    html = """
    <h2>Welcome to the AI Complaint Backend API</h2>
    <p>Available endpoints:</p>
    <ul>
        <li><a href="/admin/">/admin/</a> - Django Admin</li>
        <li><a href="/api/complaints/">/api/complaints/</a> - List all complaints (GET)</li>
        <li><a href="/api/complaints/create/">/api/complaints/create/</a> - Create a new complaint (POST)</li>
        <li><a href="/api/complaints/&lt;complaint_id&gt;/">/api/complaints/&lt;complaint_id&gt;/</a> - Retrieve a complaint (GET)</li>
        <li><a href="/api/complaints/&lt;complaint_id&gt;/update/">/api/complaints/&lt;complaint_id&gt;/update/</a> - Update a complaint (PATCH)</li>
        <li><a href="/api/complaints/&lt;complaint_id&gt;/delete/">/api/complaints/&lt;complaint_id&gt;/delete/</a> - Delete a complaint (DELETE)</li>
        <li><a href="/api/">/api/</a> - API Guide</li>
    </ul>
    """
    return HttpResponse(html)

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('api/', include('AiApp.urls')),
]