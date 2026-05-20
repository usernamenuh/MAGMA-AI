import json

def extract_incorrect_predictions(file_path):
    try:
        # Load the JSON data
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Check if 'detailed_results' exists
        if 'detailed_results' not in data:
            print("Error: 'detailed_results' key not found in JSON.")
            return

        print(f"--- Incorrect Predictions (correct: false) ---\n")

        found_any = False
        
        # Iterate through results and filter for correct == False
        for result in data['detailed_results']:
            if result.get('correct') is False:
                found_any = True
                print(f"input: {result.get('input')}")
                print(f"predicted: {result.get('predicted')}")
                print(f"expected: {result.get('expected')}")
                print("-" * 20) # Separator line

        if not found_any:
            print("No incorrect predictions found.")

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from '{file_path}'.")

# Run the function
# Ensure 'inference_result.json' is in the same directory
if __name__ == "__main__":
    extract_incorrect_predictions('inference_logs/inference_20260126_051043_results.json')