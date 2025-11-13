import Navbar from "@/components/navbar";
import Image from "next/image";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center relative overflow-hidden">
      <Navbar />
      {/* Hero Section */}
      <div className="relative flex flex-col items-center justify-center h-screen w-full text-center px-4 bg-foreground overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <Image
            src="/bg.jpg"
            alt="background"
            fill
            priority
            className="object-cover opacity-30 blur-[2px]"
          />
          <div className="absolute inset-0 bg-gradient-radial from-blue-900/20 via-purple-900/10 to-black mix-blend-overlay" />
        </div>

        <div className="max-w-4xl flex flex-col items-center justify-center">
          <h1 className="text-5xl font-weird text-white">Start creating.</h1>
          <p>Transform Hours of Footage into Minutes of Magic.</p>
        </div>
      </div>

      <div className="h-screen max-w-5xl flex flex-col items-center justify-start px-4 text-center">
        <div className="flex flex-col justify-center items-center mt-32 gap-4">
          <h1 className="font-serif text-7xl">
            Create short videos from long ones in a single click
          </h1>
          <p className="text-muted-foreground font-sans">
            A tool that can create short videos from long ones before you can
            say <span className="font-weird">Adabra Kadabra</span>
          </p>
        </div>
        <div className="h-screen w-full max-w-5xl">
          <h1 className="font-serif text-7xl">
            Built to work the way humans do
          </h1>
          <p className="text-muted-foreground font-sans">
            Autocut's multi-pass system utilizes Whisper model and Diarization
            for <span className="font-weird">seamless</span> video editing.
          </p>
        </div>
      </div>
    </div>
  );
}
