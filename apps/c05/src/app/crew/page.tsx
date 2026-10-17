"use client";

import { CrewInspection } from "@/components/crew-inspection";
import { HowItWorks } from "@/components/how-it-works";
import { PageHeader } from "@/components/page-header";
import { PhotoGuide } from "@/components/photo-guide";
import { useSession } from "@/components/providers";

export default function CrewPage() {
  const { role, kitchenId } = useSession();
  return (
    <div className="mx-auto w-full max-w-[1120px]">
      <PageHeader
        step={1}
        stage="Before serving · Kitchen crew"
        title={`Check a meal at ${kitchenId}`}
        gap="Trays are checked by eye and nothing is recorded, so a missing component is only noticed after a child has eaten."
        goal="Photograph one tray. It is compared with today's meal list and the result goes to a supervisor."
      />
      <div className="mt-4">
        <HowItWorks
          open={false}
          steps={[
            { title: "Check the list", body: "The expected components show what every tray must contain." },
            { title: "Take a photo", body: "Camera or file. Whole tray, good light." },
            { title: "Run the check", body: "See which components are present or missing. A supervisor confirms it." },
            { title: "Hand off", body: "A supervisor reviews it in Review. Uncertain? Retake the photo." },
          ]}
        />
      </div>
      <div className="mt-4 grid gap-5 lg:grid-cols-[minmax(0,560px)_minmax(0,1fr)] lg:items-start">
        <div className="min-w-0">
          <CrewInspection role={role} kitchenId={kitchenId} />
        </div>
        <aside className="min-w-0 lg:sticky lg:top-20">
          <PhotoGuide />
        </aside>
      </div>
    </div>
  );
}
