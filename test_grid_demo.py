"""
Quick demonstration of the 2D grid landing zone simulation
"""
from src.landing_controller import LandingController

print("=" * 60)
print("AutoLandrone 2D Grid Simulation Demo")
print("=" * 60)

# Create controller with grid simulation
controller = LandingController(use_grid_simulation=True, grid_size=7)

print("\n[Scenario 1: Clean landing zone - no obstacles]")
print("-" * 60)
controller.set_grid_obstacles([])
state, action, reason = controller.process_telemetry(15.0, 0.8)
print(f"Battery: 15% (Critical)")
print(f"Obstacle: 0.8m (Unsafe)")
print(f"Result: {action}")
print(f"Reason: {reason}")
print("\nGrid Layout:")
print(controller.render_grid_ascii())

print("\n" + "=" * 60)
print("[Scenario 2: Partial obstacles - find nearest safe cell]")
print("-" * 60)
controller = LandingController(use_grid_simulation=True, grid_size=7)
controller.set_grid_obstacles([(2, 3), (3, 2), (4, 3)])
state, action, reason = controller.process_telemetry(15.0, 0.8)
print(f"Battery: 15% (Critical)")
print(f"Obstacle: 0.8m (Unsafe)")
print(f"Obstacles at: (2,3), (3,2), (4,3)")
print(f"Result: {action}")
print(f"Reason: {reason}")
print("\nGrid Layout:")
print(controller.render_grid_ascii())

print("\n" + "=" * 60)
print("[Scenario 3: All cells blocked - hold and alert]")
print("-" * 60)
controller = LandingController(use_grid_simulation=True, grid_size=7)
all_blocked = [(r, c) for r in range(1, 6) for c in range(1, 6) if (r, c) != (3, 3)]
controller.set_grid_obstacles(all_blocked)
state, action, reason = controller.process_telemetry(15.0, 0.8)
print(f"Battery: 15% (Critical)")
print(f"Obstacle: 0.8m (Unsafe)")
print(f"All cells within radius 2 blocked!")
print(f"Result: {action}")
print(f"Reason: {reason}")
print("\nGrid Layout:")
print(controller.render_grid_ascii())

print("\n" + "=" * 60)
print("Grid Simulation Demo Complete!")
print("=" * 60)
print("\nTo run the full interactive dashboard:")
print("  streamlit run app.py")
print("\nTo run all tests:")
print("  pytest tests/ -v")
