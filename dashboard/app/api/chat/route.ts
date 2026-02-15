import Anthropic from '@anthropic-ai/sdk';
import { NextRequest, NextResponse } from 'next/server';

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

const PIXABAY_API_KEY = process.env.PIXABAY_API_KEY;
const PLACEHOLDER_IMAGE = '/images/dishes/placeholder.png';

interface PixabayHit {
  id: number;
  webformatURL: string;
  largeImageURL: string;
  previewURL: string;
}

interface PixabayResponse {
  total: number;
  totalHits: number;
  hits: PixabayHit[];
}

async function fetchFoodImage(mealName: string): Promise<string> {
  if (!PIXABAY_API_KEY) {
    console.warn('PIXABAY_API_KEY not set, using placeholder image');
    return PLACEHOLDER_IMAGE;
  }

  try {
    const url = new URL('https://pixabay.com/api/');
    url.searchParams.set('key', PIXABAY_API_KEY);
    url.searchParams.set('q', mealName);
    url.searchParams.set('image_type', 'photo');
    url.searchParams.set('category', 'food');
    url.searchParams.set('per_page', '3');

    const response = await fetch(url.toString());

    if (!response.ok) {
      console.error(`Pixabay API error: ${response.status}`);
      return PLACEHOLDER_IMAGE;
    }

    const data: PixabayResponse = await response.json();

    if (data.hits && data.hits.length > 0) {
      return data.hits[0].webformatURL;
    }

    return PLACEHOLDER_IMAGE;
  } catch (error) {
    console.error('Error fetching image from Pixabay:', error);
    return PLACEHOLDER_IMAGE;
  }
}

export async function POST(request: NextRequest) {
  try {
    const { message, preferences } = await request.json();

    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    // Build system prompt with user preferences
    const preferencesText = preferences && preferences.length > 0
      ? `The user has the following dietary preferences and restrictions: ${preferences.join(', ')}.`
      : 'The user has no specific dietary preferences.';

    const systemPrompt = `You are a helpful cooking assistant. ${preferencesText}

When the user asks what to cook or requests meal recommendations, provide 3 specific meal suggestions that match their preferences and request.

Return your response in the following JSON format:
{
  "recommendations": [
    {
      "name": "Meal Name",
      "description": "Brief description of the dish",
      "imageUrl": "/images/dishes/placeholder.png"
    }
  ],
  "message": "A friendly response to the user's request"
}

Make sure the meal names are specific and appealing. Consider the user's preferences when making recommendations.`;

    const response = await anthropic.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 1024,
      system: systemPrompt,
      messages: [
        {
          role: 'user',
          content: message,
        },
      ],
    });

    // Extract the text content from Claude's response
    const textContent = response.content[0];
    if (textContent.type !== 'text') {
      throw new Error('Unexpected response format from Claude');
    }

    // Parse the JSON response from Claude
    let parsedResponse;
    try {
      // Try to extract JSON from the response
      const jsonMatch = textContent.text.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        parsedResponse = JSON.parse(jsonMatch[0]);
      } else {
        // Fallback if Claude doesn't return JSON
        parsedResponse = {
          recommendations: [],
          message: textContent.text,
        };
      }
    } catch (parseError) {
      // If parsing fails, return a default response
      parsedResponse = {
        recommendations: [],
        message: textContent.text,
      };
    }

    // Fetch images from Pixabay for each recommendation
    if (parsedResponse.recommendations && parsedResponse.recommendations.length > 0) {
      const recommendationsWithImages = await Promise.all(
        parsedResponse.recommendations.map(async (rec: any) => {
          const imageUrl = await fetchFoodImage(rec.name);
          return {
            ...rec,
            imageUrl,
          };
        })
      );
      parsedResponse.recommendations = recommendationsWithImages;
    }

    return NextResponse.json(parsedResponse);
  } catch (error) {
    console.error('Error calling Anthropic API:', error);
    return NextResponse.json(
      { error: 'Failed to get recommendations' },
      { status: 500 }
    );
  }
}
