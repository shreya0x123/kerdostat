import { useLocation, useNavigate } from "react-router-dom";
import HijackPanel from "@/components/HijackPanel";

export default function HijackPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const proposal = location.state?.proposal;

  const handleSuccess = () => {
    setTimeout(() => {
      navigate("/dashboard");
    }, 1500);
  };

  return (
    <div className="w-full max-w-4xl mx-auto py-8 space-y-6">
      <div className="rounded-2xl border border-border bg-card p-6 md:p-8 shadow-sm">
        <h2 className="text-2xl font-bold text-foreground mb-2">Execution Hijack Engine</h2>
        <p className="text-xs text-muted-foreground mb-6 font-sans">
          This manual control panel permits execution overriding and bypasses the active algo loop for emergency trading action.
        </p>

        <HijackPanel proposal={proposal} onSuccess={handleSuccess} />
      </div>
    </div>
  );
}
