import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Mail,
  MapPin,
  Send,
  CheckCircle,
  MessageSquare,
  ArrowRight,
  Clock,
  ExternalLink
} from "lucide-react";

export default function ContactPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    organization: "",
    useCase: "brokers",
    message: ""
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.name || !formData.email || !formData.message) {
      alert("Please fill in all required fields.");
      return;
    }
    
    setIsSubmitting(true);
    
    // Simulate API request
    setTimeout(() => {
      setIsSubmitting(false);
      setSubmitSuccess(true);
    }, 1200);
  };

  const handleReset = () => {
    setFormData({
      name: "",
      email: "",
      organization: "",
      useCase: "brokers",
      message: ""
    });
    setSubmitSuccess(false);
  };

  return (
    <div className="w-full max-w-5xl mx-auto py-8 px-4 font-sans space-y-12">
      {/* Header */}
      <section className="space-y-4 text-left max-w-3xl">
        <div className="flex items-center gap-2">
          <span className="inline-block rounded-full bg-primary/10 text-primary border border-primary/20 px-3 py-1 text-xs font-semibold uppercase tracking-wider">
            Contact Us
          </span>
          <span className="h-px w-8 bg-border" />
          <span className="text-xs text-muted-foreground">Typically responds in under 2 hours</span>
        </div>
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-foreground">
          Let's build something <span className="text-primary">secure</span> together
        </h1>
        <p className="text-lg text-muted-foreground leading-relaxed">
          Have questions about Kerdostat’s execution pipeline, compliance layers, or looking for dedicated API limits? Get in touch with our engineering team.
        </p>
      </section>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-12 pt-4">
        {/* Left Column: Form / Success Card */}
        <div className="rounded-2xl border border-border bg-card p-6 md:p-8 shadow-sm relative overflow-hidden transition-all duration-300">
          {submitSuccess ? (
            <div className="flex flex-col items-center justify-center text-center py-12 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
              <div className="h-16 w-16 rounded-full bg-primary/15 border border-primary/20 text-primary grid place-items-center mb-2">
                <CheckCircle className="h-8 w-8" />
              </div>
              <div className="space-y-2">
                <h2 className="text-2xl font-bold text-foreground">Inquiry Received</h2>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  Thank you for reaching out, <span className="font-semibold text-foreground">{formData.name}</span>. An engineer from our integrations desk will get back to you at <span className="font-semibold text-foreground">{formData.email}</span> shortly.
                </p>
              </div>

              {/* Submitted Details Summary Card */}
              <div className="w-full max-w-sm rounded-xl border border-border bg-secondary/30 p-4 text-left text-xs space-y-2.5">
                <div className="flex justify-between border-b border-border/55 pb-2">
                  <span className="text-muted-foreground">Organization</span>
                  <span className="font-semibold text-foreground">{formData.organization || "Not Specified"}</span>
                </div>
                <div className="flex justify-between border-b border-border/55 pb-2">
                  <span className="text-muted-foreground">Target Use Case</span>
                  <span className="font-semibold text-foreground capitalize">
                    {formData.useCase === "brokers" && "Brokers & Wealth"}
                    {formData.useCase === "banks" && "Banks & EMIs"}
                    {formData.useCase === "software" && "Software Ecosystem"}
                    {formData.useCase === "other" && "Other Solutions"}
                  </span>
                </div>
                <div className="pt-1 text-muted-foreground italic line-clamp-3">
                  "{formData.message}"
                </div>
              </div>

              <button
                type="button"
                onClick={handleReset}
                className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-5 py-2.5 text-xs font-bold text-foreground hover:bg-secondary/50 active:scale-98 transition"
              >
                Send Another Message
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Name */}
                <div className="space-y-2">
                  <label htmlFor="name" className="text-xs font-bold text-foreground uppercase tracking-wider">
                    Full Name <span className="text-primary">*</span>
                  </label>
                  <input
                    id="name"
                    type="text"
                    required
                    placeholder="Jane Doe"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/45 transition"
                  />
                </div>

                {/* Email */}
                <div className="space-y-2">
                  <label htmlFor="email" className="text-xs font-bold text-foreground uppercase tracking-wider">
                    Work Email <span className="text-primary">*</span>
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    placeholder="jane@company.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/45 transition"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Organization */}
                <div className="space-y-2">
                  <label htmlFor="organization" className="text-xs font-bold text-foreground uppercase tracking-wider">
                    Organization
                  </label>
                  <input
                    id="organization"
                    type="text"
                    placeholder="Acme Corp"
                    value={formData.organization}
                    onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                    className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/45 transition"
                  />
                </div>

                {/* Use Case */}
                <div className="space-y-2">
                  <label htmlFor="useCase" className="text-xs font-bold text-foreground uppercase tracking-wider">
                    Primary Use Case
                  </label>
                  <select
                    id="useCase"
                    value={formData.useCase}
                    onChange={(e) => setFormData({ ...formData, useCase: e.target.value })}
                    className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/45 transition cursor-pointer appearance-none"
                    style={{
                      backgroundImage: `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='hsl(168, 12%, 45%)' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'></polyline></svg>")`,
                      backgroundRepeat: "no-repeat",
                      backgroundPosition: "right 12px center",
                      backgroundSize: "16px"
                    }}
                  >
                    <option value="brokers">Brokers & Wealth Managers</option>
                    <option value="banks">Banks & EMIs</option>
                    <option value="software">Software Companies</option>
                    <option value="other">Other Solution</option>
                  </select>
                </div>
              </div>

              {/* Message */}
              <div className="space-y-2">
                <label htmlFor="message" className="text-xs font-bold text-foreground uppercase tracking-wider">
                  How can we help? <span className="text-primary">*</span>
                </label>
                <textarea
                  id="message"
                  required
                  rows={4}
                  placeholder="Tell us about your technical stack, integration timeline, or volume requirements..."
                  value={formData.message}
                  onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                  className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/45 transition resize-none"
                />
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-sm font-bold text-primary-foreground hover:brightness-105 active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none transition shadow-lg shadow-primary/10"
              >
                {isSubmitting ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                    <span>Transmitting inquiry...</span>
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4" />
                    <span>Submit Inquiry</span>
                  </>
                )}
              </button>
            </form>
          )}
        </div>

        {/* Right Column: Coordinate details / Trust Elements */}
        <div className="flex flex-col gap-6">
          {/* Coordinates Card */}
          <div className="rounded-2xl border border-border bg-card/50 p-6 space-y-6">
            <h3 className="text-lg font-bold text-foreground">Developer Support Desk</h3>
            
            <div className="space-y-4">
              {/* Direct Mail */}
              <div className="flex items-start gap-3.5">
                <div className="h-8 w-8 rounded-lg bg-primary/10 border border-primary/20 text-primary grid place-items-center flex-shrink-0">
                  <Mail className="h-4 w-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wide">Email Inquiries</h4>
                  <a href="mailto:hello@kerdostat.com" className="text-sm font-semibold text-foreground hover:text-primary transition">
                    hello@kerdostat.com
                  </a>
                </div>
              </div>

              {/* Hours */}
              <div className="flex items-start gap-3.5">
                <div className="h-8 w-8 rounded-lg bg-secondary text-primary grid place-items-center flex-shrink-0">
                  <Clock className="h-4 w-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wide">Desk Hours</h4>
                  <p className="text-sm font-semibold text-foreground">
                    08:00 – 22:00 IST / UTC+5.5
                  </p>
                </div>
              </div>

              {/* Head office location */}
              <div className="flex items-start gap-3.5">
                <div className="h-8 w-8 rounded-lg bg-secondary text-primary grid place-items-center flex-shrink-0">
                  <MapPin className="h-4 w-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wide">Office</h4>
                  <p className="text-sm font-semibold text-foreground leading-relaxed">
                    Tech Park Main, Phase 2<br />
                    Bangalore, KA 560103
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Quick link Card */}
          <div className="rounded-2xl border border-border bg-secondary/20 p-6 flex flex-col justify-between space-y-4 relative overflow-hidden group">
            <div className="absolute top-0 right-0 h-24 w-24 bg-primary/5 rounded-full blur-2xl -mr-6 -mt-6 group-hover:bg-primary/10 transition-colors" />
            <div className="space-y-2">
              <span className="text-[10px] uppercase tracking-[0.25em] text-primary font-bold">API Documentation</span>
              <h4 className="text-base font-bold text-foreground">Check the Sandbox Guides</h4>
              <p className="text-xs text-muted-foreground leading-relaxed font-sans">
                Curious to see what properties our API returns? Learn how to stream logs, authenticate webhooks, and launch paper execution loops directly.
              </p>
            </div>
            <Link
              to="/docs"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-primary hover:gap-2 transition pt-2"
            >
              <span>Browse Developer Docs</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {/* Direct Support */}
          <div className="rounded-2xl border border-border bg-card/30 p-6 flex flex-col gap-4">
            <div className="flex items-center gap-2.5">
              <MessageSquare className="h-4 w-4 text-primary" />
              <h4 className="text-sm font-bold text-foreground">Need Urgent Technical Assist?</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed font-sans">
              If your execution loop is throwing exceptions or order updates aren't arriving, please bypass the form and ping our Telegram Support gateway directly.
            </p>
            <a
              href="https://t.me/kerdostat_dev"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-border bg-card hover:bg-secondary/50 px-4 py-2.5 text-xs font-bold text-foreground transition"
            >
              <span>Open Telegram Channel</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
