# NutriPilot AI 🥗

Your Autonomous Nutrition Co-Pilot - An AI-powered meal analysis system built for the **Commit to Change Hackathon**.

![NutriPilot Landing](https://via.placeholder.com/800x400/0a0a0f/10b981?text=NutriPilot+AI)

## 🚀 Features

- **📷 Food Image Analysis**: Snap a photo and get instant AI-powered nutritional breakdown
- **🎯 Pixel-Precise Portions**: Gemini 2.0 Vision estimates portion sizes accurately
- **🧬 Bio-Data Integration**: Personalized recommendations based on health constraints
- **⚡ Real-Time Streaming**: Vercel AI SDK for responsive 30+ second agent chains
- **📊 Opik Observability**: Full tracing and evaluation pipeline

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14, React, Tailwind CSS |
| AI SDK | Vercel AI SDK with Gemini 2.0 Flash |
| Streaming | Server-Sent Events for real-time updates |
| Styling | Glassmorphism dark theme |
| Deployment | Vercel |

## 🏃 Quick Start

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/nutripilot.git
cd nutripilot/frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your API keys

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the app.

## 🔑 Environment Variables

Create a `.env.local` file with:

```bash
# Required
GOOGLE_GENERATIVE_AI_API_KEY=your_gemini_api_key

# Optional (for enhanced features)
OPIK_API_KEY=your_opik_api_key
USDA_API_KEY=your_usda_api_key
```

### Getting API Keys

1. **Google Gemini**: [Get API Key](https://aistudio.google.com/app/apikey)
2. **Comet Opik**: [Sign Up](https://www.comet.com/)
3. **USDA FoodData**: [Request Key](https://fdc.nal.usda.gov/api-key-signup.html)

## 📁 Project Structure

```
frontend/
├── app/
│   ├── api/analyze/route.ts   # Streaming AI endpoint
│   ├── globals.css            # Design system
│   ├── layout.tsx             # Root layout
│   └── page.tsx               # Main app page
├── components/
│   ├── ImageUpload.tsx        # Drag & drop uploader
│   ├── AnalysisResults.tsx    # Results display
│   └── StreamingAnalysis.tsx  # Real-time streaming UI
├── types/
│   └── meal.ts                # TypeScript interfaces
└── .env.example               # Environment template
```

## 🔄 How It Works

1. **Upload**: Drag & drop a meal photo
2. **Analyze**: Gemini Vision identifies foods and portions
3. **Lookup**: AI agents query nutrition database
4. **Score**: Health constraints checked, meal scored
5. **Display**: Results stream in real-time

## 🏆 Hackathon

Built for **Commit to Change: An AI Agents Hackathon** by Encode Club x Comet.

- **Theme**: AI tools for achieving New Year's resolutions
- **Focus**: Health & nutrition goal tracking
- **Tech**: Gemini 2.0, Opik observability, Vercel streaming

## 📄 License

MIT

---

**Built with ❤️ for a healthier future**
