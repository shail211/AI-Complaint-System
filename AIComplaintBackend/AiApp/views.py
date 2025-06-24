from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from bson import ObjectId
import json
from datetime import datetime
from .db import complaints_collection
from .ai_model import analyze_complaint

@csrf_exempt
def complaint_list(request):
    """Handle GET requests to list all complaints and provide status counts"""
    if request.method == 'GET':
        try:
            complaints = list(complaints_collection.find())
            # Convert ObjectId to string for JSON serialization
            for complaint in complaints:
                complaint['_id'] = str(complaint['_id'])

            # Count complaints by status (case-insensitive, support all variants)
            total_complaints = len(complaints)
            pending_review = sum(1 for c in complaints if str(c.get('status', '')).lower() in ['pending', 'pending_review', 'under_review'])
            resolved = sum(1 for c in complaints if str(c.get('status', '')).lower() in ['resolved'])
            in_progress = sum(1 for c in complaints if str(c.get('status', '')).lower() in ['in_progress'])
            rejected = sum(1 for c in complaints if str(c.get('status', '')).lower() in ['rejected'])
            return JsonResponse({
                'total_complaints': total_complaints,
                'pending_review': pending_review,
                'resolved': resolved,
                'in_progress': in_progress,
                'rejected': rejected,
                'complaints': complaints
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def complaint_create(request):
    """Handle POST requests to create a new complaint"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Add timestamp
            data['time'] = datetime.now().strftime('%H:%M')
            data['date'] = datetime.now().strftime('%Y-%m-%d')
            
            # Validate required fields
            required_fields = ['profile_name', 'complaint_query']
            if not all(field in data for field in required_fields):
                return JsonResponse({'error': 'Missing required fields'}, status=400)

            # AI inference for complaint analysis
            ai_result = analyze_complaint(data['complaint_query'])
            if ai_result is None:
                return JsonResponse({'error': 'AI analysis failed'}, status=500)
            data['priority_score'] = ai_result.get('priority_score', 1)
            data['department'] = ai_result.get('department', 'General')
            data['recommended_officer'] = ai_result.get('recommended_officer', '')
            data['ai_analysis'] = ai_result.get('ai_analysis', {})
            data['status'] = 'pending_review'  # Default status
            
            result = complaints_collection.insert_one(data)
            return JsonResponse({
                'message': 'Complaint created successfully',
                'id': str(result.inserted_id)
            }, status=201)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def complaint_detail(request, complaint_id):
    """Handle GET requests for a specific complaint"""
    if request.method == 'GET':
        try:
            complaint = complaints_collection.find_one({'_id': ObjectId(complaint_id)})
            if complaint:
                complaint['_id'] = str(complaint['_id'])
                return JsonResponse(complaint)
            return JsonResponse({'error': 'Complaint not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def complaint_update(request, complaint_id):
    """Handle PATCH requests to update a complaint"""
    if request.method == 'PATCH':
        try:
            data = json.loads(request.body)
            # Only allow status to be updated to allowed values
            allowed_statuses = ['resolved', 'pending_review', 'in_progress', 'rejected', 'under_review']
            if 'status' in data and data['status'] not in allowed_statuses:
                return JsonResponse({'error': 'Invalid status value'}, status=400)
            result = complaints_collection.update_one(
                {'_id': ObjectId(complaint_id)},
                {'$set': data}
            )
            if result.modified_count:
                return JsonResponse({'message': 'Complaint updated successfully'})
            return JsonResponse({'error': 'Complaint not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def complaint_delete(request, complaint_id):
    """Handle DELETE requests to remove a complaint"""
    if request.method == 'DELETE':
        try:
            result = complaints_collection.delete_one({'_id': ObjectId(complaint_id)})
            if result.deleted_count:
                return JsonResponse({'message': 'Complaint deleted successfully'})
            return JsonResponse({'error': 'Complaint not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def api_guide(request):
    html = '''
    <html>
    <head>
        <title>AI Complaint Backend API Guide</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f8f9fa; color: #222; margin: 0; padding: 0; }
            .container { max-width: 800px; margin: 40px auto; background: #fff; border-radius: 10px; box-shadow: 0 2px 8px #0001; padding: 32px; }
            h1 { color: #2a7ae2; }
            h2 { color: #444; margin-top: 2em; }
            pre { background: #f4f4f4; padding: 12px; border-radius: 6px; overflow-x: auto; }
            .endpoint { margin-bottom: 2em; }
            .method { font-weight: bold; color: #fff; background: #2a7ae2; padding: 2px 8px; border-radius: 4px; margin-right: 8px; }
            .path { font-family: monospace; color: #2a7ae2; }
            .desc { margin: 8px 0 8px 0; }
            .sample { margin: 4px 0 4px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AI Complaint Backend API Guide</h1>
            <div class="endpoint">
                <span class="method">GET</span> <span class="path">/api/complaints/</span>
                <div class="desc">List all complaints.</div>
            </div>
            <div class="endpoint">
                <span class="method">POST</span> <span class="path">/api/complaints/create/</span>
                <div class="desc">Create a new complaint. <b>Required fields:</b> <code>profile_name</code>, <code>complaint_query</code>. AI fields and status are auto-filled.</div>
                <div class="sample"><b>Sample request:</b>
                    <pre>{
  "profile_name": "John Doe",
  "complaint_query": "There is a water leakage in the main hall."
}</pre>
                </div>
                <div class="sample"><b>Sample response:</b>
                    <pre>{
  "message": "Complaint created successfully",
  "id": "&lt;inserted_id&gt;"
}</pre>
                </div>
            </div>
            <div class="endpoint">
                <span class="method">GET</span> <span class="path">/api/complaints/&lt;complaint_id&gt;/</span>
                <div class="desc">Get details of a specific complaint by its ID.</div>
            </div>
            <div class="endpoint">
                <span class="method">PATCH</span> <span class="path">/api/complaints/&lt;complaint_id&gt;/update/</span>
                <div class="desc">Update a complaint. You can update the <code>status</code> field to one of: <b>under_review</b>, <b>resolved</b>, <b>rejected</b>.</div>
                <div class="sample"><b>Sample request:</b>
                    <pre>{
  "status": "resolved"
}</pre>
                </div>
                <div class="sample"><b>Sample response:</b>
                    <pre>{
  "message": "Complaint updated successfully"
}</pre>
                </div>
            </div>
            <div class="endpoint">
                <span class="method">DELETE</span> <span class="path">/api/complaints/&lt;complaint_id&gt;/delete/</span>
                <div class="desc">Delete a complaint by its ID.</div>
            </div>
        </div>
    </body>
    </html>
    '''
    return HttpResponse(html)