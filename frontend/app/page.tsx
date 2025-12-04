'use client';

import { useState } from 'react';
import { buildWorkflow } from '../lib/workflow';
import Image from 'next/image';

interface GeneratedImage {
  node_id: string;
  data: string;
  url?: string;
}

export default function Home() {
  const [prompt, setPrompt] = useState('anime cat with massive fluffy fennec ears');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [width, setWidth] = useState(512);
  const [height, setHeight] = useState(512);
  const [seed, setSeed] = useState(123456789);
  const [loading, setLoading] = useState(false);
  const [generatedImages, setGeneratedImages] = useState<GeneratedImage[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setGeneratedImages([]);

    if (width % 64 !== 0 || height % 64 !== 0) {
      setError('Width and Height must be multiples of 64.');
      setLoading(false);
      return;
    }

    try {
      const workflow = buildWorkflow({
        prompt,
        negativePrompt,
        width,
        height,
        seed,
      });

      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ workflow }),
      });

      if (!response.ok) {
        throw new Error(`Error: ${response.statusText}`);
      }

      const data = await response.json();
      setGeneratedImages(data.images || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-extrabold text-gray-900">
            Image Generation
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Customize your image generation parameters below.
          </p>
        </div>

        <div className="bg-white shadow sm:rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <form onSubmit={handleSubmit} className="space-y-6" noValidate>
              <div>
                <label htmlFor="prompt" className="block text-sm font-medium text-gray-700">
                  Positive Prompt
                </label>
                <div className="mt-1">
                  <textarea
                    id="prompt"
                    name="prompt"
                    rows={3}
                    className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md border p-2"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div>
                <label htmlFor="negativePrompt" className="block text-sm font-medium text-gray-700">
                  Negative Prompt
                </label>
                <div className="mt-1">
                  <textarea
                    id="negativePrompt"
                    name="negativePrompt"
                    rows={2}
                    className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md border p-2"
                    value={negativePrompt}
                    onChange={(e) => setNegativePrompt(e.target.value)}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-3">
                <div>
                  <label htmlFor="width" className="block text-sm font-medium text-gray-700">
                    Width
                  </label>
                  <div className="mt-1">
                    <input
                      type="number"
                      name="width"
                      id="width"
                      className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md border p-2"
                      value={width}
                      onChange={(e) => setWidth(parseInt(e.target.value))}
                      step={64}
                      min={64}
                      required
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="height" className="block text-sm font-medium text-gray-700">
                    Height
                  </label>
                  <div className="mt-1">
                    <input
                      type="number"
                      name="height"
                      id="height"
                      className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md border p-2"
                      value={height}
                      onChange={(e) => setHeight(parseInt(e.target.value))}
                      step={64}
                      min={64}
                      required
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="seed" className="block text-sm font-medium text-gray-700">
                    Seed
                  </label>
                  <div className="mt-1">
                    <input
                      type="number"
                      name="seed"
                      id="seed"
                      className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md border p-2"
                      value={seed}
                      onChange={(e) => setSeed(parseInt(e.target.value))}
                      required
                    />
                  </div>
                </div>
              </div>

              {error && (
                <div className="rounded-md bg-red-50 p-4">
                  <div className="flex">
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-red-800">Error</h3>
                      <div className="mt-2 text-sm text-red-700">
                        <p>{error}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div>
                <button
                  type="submit"
                  disabled={loading}
                  className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
                    loading ? 'bg-indigo-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'
                  }`}
                >
                  {loading ? 'Generating...' : 'Generate'}
                </button>
              </div>
            </form>
          </div>
        </div>

        {generatedImages.length > 0 && (
          <div className="bg-white shadow sm:rounded-lg overflow-hidden">
             <div className="px-4 py-5 sm:px-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900">Generated Images</h3>
             </div>
            <div className="px-4 py-5 sm:p-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {generatedImages.map((img, idx) => (
                <div key={idx} className="relative aspect-square bg-gray-200 rounded-lg overflow-hidden">
                    {/* If we have a URL use it, otherwise use base64 data uri */}
                  <Image
                    src={img.url ? img.url : `data:image/png;base64,${img.data}`}
                    alt={`Generated image ${idx + 1}`}
                    fill
                    className="object-cover"
                  />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
