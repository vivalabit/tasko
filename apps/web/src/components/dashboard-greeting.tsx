"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

export function useHydrationSafeCurrentTime() {
  const [currentTime, setCurrentTime] = useState<Date | null>(null);

  useEffect(() => {
    setCurrentTime(new Date());
    const interval = window.setInterval(
      () => setCurrentTime(new Date()),
      60_000,
    );
    return () => window.clearInterval(interval);
  }, []);

  return currentTime;
}

export function DashboardGreeting({
  name,
  currentTime,
}: {
  name: string;
  currentTime: Date | null;
}) {
  const firstName = name.trim().split(/\s+/)[0] ?? "";
  const hour = currentTime?.getHours();
  const timeOfDay =
    hour === undefined
      ? {
          greeting: "Hello",
          titleClassName: "from-white via-[#fff0e3] to-[#ff9e4f]",
        }
      : hour >= 5 && hour < 12
        ? {
            greeting: "Good morning",
            titleClassName: "from-white via-[#fff4de] to-[#ffc66f]",
          }
        : hour >= 12 && hour < 17
          ? {
              greeting: "Good afternoon",
              titleClassName: "from-white via-[#fff0e3] to-[#ff9e4f]",
            }
          : hour >= 17 && hour < 22
            ? {
                greeting: "Good evening",
                titleClassName: "from-white via-[#f8eaff] to-[#d7a0ff]",
              }
            : {
                greeting: "Hello, night owl",
                titleClassName: "from-white via-[#eaf2ff] to-[#91bbff]",
              };

  return (
    <h1
      className={cn(
        "bg-gradient-to-r bg-clip-text text-[24px] font-bold leading-tight tracking-normal text-transparent sm:text-[27px] 2xl:text-[31px]",
        timeOfDay.titleClassName,
      )}
    >
      {timeOfDay.greeting}
      {firstName ? `, ${firstName}` : ""}!
    </h1>
  );
}
