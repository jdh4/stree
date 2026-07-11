"""Generate by Gemini 3.1 Pro"""

import subprocess

class SprioWeights:
    """
    A class to capture and parse Slurm sprio weights.
    """
    def __init__(self):
        # Dictionary to store the parsed weights
        self.weights = {}

    def parse_text(self, sprio_output: str) -> dict:
        """
        Parses the text output of `sprio -w` and updates the dictionary.
        """
        lines = sprio_output.strip().split('\n')

        # Ensure we have at least a header line and a data line
        if len(lines) < 2:
            return self.weights

        # Split the header and the weights data by whitespace
        headers = lines[0].split()
        weights_data = lines[1].split()

        # The first item in the data row is usually the word "Weights"
        if weights_data and weights_data[0] == "Weights":
            weights_values = weights_data[1:]
        else:
            weights_values = weights_data

        # Map the values to the last N headers
        # (Skips headers on the left that don't have assigned weights)
        num_values = len(weights_values)
        if num_values == 0:
            return self.weights

        relevant_headers = headers[-num_values:]

        # Clear existing weights and populate with new ones
        self.weights.clear()
        for header, value in zip(relevant_headers, weights_values):
            # Convert numeric strings to integers, keep complex strings (like TRES) as-is
            try:
                self.weights[header] = int(value)
            except ValueError:
                self.weights[header] = value

        return self.weights

    def fetch_live(self) -> dict:
        """
        Runs the `sprio -w` command on a Slurm system and updates the dictionary.
        """
        try:
            result = subprocess.run(
                ['sprio', '-w'],
                capture_output=True,
                text=True,
                check=True
            )
            return self.parse_text(result.stdout)
        except FileNotFoundError:
            print("Error: 'sprio' command not found. Are you on a Slurm system?")
            return {}
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")
            return {}

    def get_weight(self, factor_name: str):
        """
        Retrieves the weight for a specific factor (e.g., 'AGE', 'FAIRSHARE').
        """
        return self.weights.get(factor_name.upper())

    def __str__(self):
        """
        Returns a formatted string of the current weights.
        """
        if not self.weights:
            return "No weights loaded."

        output = ["Current Sprio Weights:"]
        for factor, weight in self.weights.items():
            output.append(f"  {factor}: {weight}")
        return "\n".join(output)


# ==========================================
# Example usage
# ==========================================
if __name__ == "__main__":
    sample_output = """
         JOBID PARTITION   PRIORITY       SITE        AGE  FAIRSHARE    JOBSIZE  PARTITION        QOS                 TRES
       Weights                              1      10000      12000      10000          1       8000 CPU=1,Mem=1,GRES/gpu
    """

    # Initialize the class
    sprio_tracker = SprioWeights()

    # 1. Parse from the sample text
    sprio_tracker.parse_text(sample_output)

    # Print all weights using the __str__ method
    print(sprio_tracker)
    print("-" * 30)

    # Get a specific weight
    age_weight = sprio_tracker.get_weight("AGE")
    print(f"The weight for AGE is: {age_weight}")

    # 2. To fetch live data on your cluster, uncomment below:
    sprio_tracker.fetch_live()
    print(sprio_tracker.weights)
