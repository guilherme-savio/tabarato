import { motion } from "framer-motion";

type InfoLabelProps = {
  text: string;
  color?: "primary" | "secondary" | "accent" | "success" | "warning" | "error";
};

const InfoLabelMobile = ({ text, color = "primary" }: InfoLabelProps) => {
  return (
    <motion.div
        initial={{ x: -150, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ type: "spring", stiffness: 150, damping: 18 }}
        whileHover={{ scale: 1.05 }}
      className={`border-${color} bg-${color} bg-opacity-90 rounded-lg pl-2 py-2 text-sm font-semibold text-base-100 shadow-lg mb-4 text-sm md:text-base break-words whitespace-normal max-w-full`}
    >
      <motion.div
        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
      >
        {text}
      </motion.div>
    </motion.div>
  );
};

export default InfoLabelMobile;
