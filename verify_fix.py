from src.graph import graph

def test_run():
    print("Starting test run...")
    initial_state = {
        "rfp_text": "Need a website for a local bakery.",
        "status": "starting"
    }
    
    try:
        # Run the graph
        # Note: We use stream or invoke. Since it might have human review, 
        # we just want to see if it reaches the first few nodes without KeyError.
        for event in graph.stream(initial_state):
            for node, state in event.items():
                print(f"Node: {node}")
                # print(f"State: {state}")
                if "error" in state:
                    print(f"Error in state: {state['error']}")
                    return
        print("Test run completed successfully!")
    except KeyError as e:
        print(f"TEST FAILED: KeyError on {e}")
    except Exception as e:
        print(f"TEST FAILED: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_run()
