import { HealthCheck } from "@/components/health-check";

export default function HomePage() {
  return (
    <main style={{ padding: "2rem", maxWidth: "640px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 600 }}>NutriRoll</h1>
      <p style={{ marginTop: "0.5rem", opacity: 0.7 }}>
        Phase 0 placeholder — verifying connectivity to the API.
      </p>
      <section style={{ marginTop: "1.5rem" }}>
        <HealthCheck />
      </section>
    </main>
  );
}
