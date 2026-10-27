export const capabilities = [
  { icon: "CloudSun", title: "Weather intelligence", text: "Understand forecast signals and plan operations around changing conditions." },
  { icon: "Sprout", title: "Crop & soil context", text: "Bring crop requirements, field context and soil knowledge into decisions." },
  { icon: "ChartNoAxesCombined", title: "Market awareness", text: "Compare market signals and improve harvest and selling decisions." },
  { icon: "Bug", title: "Pest & disease guidance", text: "Review warning signs and evidence-based prevention practices." },
  { icon: "BookOpenText", title: "Agricultural knowledge RAG", text: "Retrieve relevant trusted guidance instead of relying on unsupported claims." },
  { icon: "BrainCircuit", title: "Explainable agent decisions", text: "Combine specialist reasoning, confidence checks and human oversight." },
];
export type Insight = { id: string; title: string; description: string; category: string; priority: "High"|"Medium"|"Low" };
export const demoInsights: Insight[] = [
  { id:"w1", title:"Review rainfall before irrigation", description:"Check an up-to-date local forecast and soil moisture conditions before watering.", category:"Weather", priority:"Medium" },
  { id:"c1", title:"Scout for leaf damage", description:"Inspect representative plants and document symptoms before choosing a treatment.", category:"Crop health", priority:"Medium" },
  { id:"m1", title:"Compare market quotations", description:"Verify current local prices from multiple sources before making a sales decision.", category:"Market", priority:"Low" },
];
