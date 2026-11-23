import { Roboto_Flex } from "next/font/google";
import "./proto.css";

const roboto = Roboto_Flex({ variable: "--font-roboto-flex", subsets: ["latin"] });

export const metadata = { title: "Prototipe UI" };

export default function ProtoLayout({ children }: { children: React.ReactNode }) {
  return <div className={`${roboto.variable} contents`}>{children}</div>;
}
