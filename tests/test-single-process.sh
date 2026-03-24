# Send first request
echo "=== Request 1 Output ==="
RESPONSE1=$(curl -s -X POST "http://localhost:5050/api/v1/process" \
  -F 'image=@data/input/creative_2.png' \
  -F 'recommendations=[{"id":"rec-1","title":"Deepen Emotional Narrative with Lifestyle Context","description":"Refine product image styling and decorative elements to communicate a desired lifestyle or emotional state—such as freedom, discovery, or personal expression—rather than surface-level fun. This elevates emotional resonance and strengthens the motivational hook driving conversion action.","type":"colour_mood"}]' \
  -F 'brand_guidelines={"protected_regions":["Do not modify or remove the brand logo"],"aspect_ratio":"Maintain original aspect ratio (636x1063)"}')
echo "$RESPONSE1"

# Send second request
echo "=== Request 2 Output ==="
RESPONSE2=$(curl -s -X POST "http://localhost:5050/api/v1/process" \
  -F 'image=@data/input/creative_1.png' \
  -F 'recommendations=[{"id":"rec-1","title":"Strengthen Headline Impact","description":"Add visual punch to the headline through enhanced color contrast, a soft gradient backdrop, or a geometric shape—without increasing its physical size. The moderate attention on the discount message suggests it needs more visual emphasis to register urgency and value immediately.","type":"contrast_salience"}]' \
  -F 'brand_guidelines={"protected_regions":["Do not modify or remove the brand logo"],"aspect_ratio":"Maintain original aspect ratio (1572x1720)"}')
echo "$RESPONSE2"